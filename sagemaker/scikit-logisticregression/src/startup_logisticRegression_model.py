from __future__ import print_function

import argparse
import os
import pandas as pd
import boto3
import io
import re
from io import StringIO
import pickle
import json
import numpy as np
from six import BytesIO

from sklearn import tree
from sklearn.externals import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, accuracy_score, f1_score, confusion_matrix, classification_report
from sklearn.feature_extraction.text import CountVectorizer
from sagemaker_containers.beta.framework import (
    content_types, encoders, env, modules, transformer, worker)

from html import unescape
from nltk.tokenize import word_tokenize
import nltk
nltk.download('punkt')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Sagemaker specific arguments. Defaults are set in the environment variables.

    # Saves Checkpoints and graphs
    parser.add_argument('--output-data-dir', type=str,
                        default=os.environ['SM_OUTPUT_DATA_DIR'])

    # Save model artifacts
    parser.add_argument('--model-dir', type=str,
                        default=os.environ['SM_MODEL_DIR'])
    
    parser.add_argument('--train', type=str,
                        default=os.environ.get('SM_CHANNEL_TRAIN'))
    
    parser.add_argument('--test', type=str,
                        default=os.environ.get('SM_CHANNEL_TEST'))
    
    args = parser.parse_args()
    
    DATASET_COLUMNS = ["sentiment", "text"]
    DATASET_ENCODING = "ISO-8859-1"
    train_dataset = pd.read_csv(os.path.join(args.train, 'sentiments-preprocessed-wo-lemmatizing-with-stopwords-train-10percent-dataset.csv'), encoding=DATASET_ENCODING, names=DATASET_COLUMNS, engine='python')
    test_dataset = pd.read_csv(os.path.join(args.test, 'sentiments-preprocessed-wo-lemmatizing-with-stopwords-test-10percent-dataset.csv'), encoding=DATASET_ENCODING, names=DATASET_COLUMNS, engine='python')
    print('Datasets read')

    # Storing data in lists.
    test_text, test_sentiment = list(
        test_dataset['text']), list(test_dataset['sentiment'])
    train_text, train_sentiment = list(
        train_dataset['text']), list(train_dataset['sentiment'])

    # Join/Merge list to vectorize
    text = train_text + test_text

    print('Vectorizing with CountVectorizer')
    vectorizer = CountVectorizer(analyzer='word', lowercase=True,)
    vectorizer.fit(text)
    text = vectorizer.transform(text)
    print('Vectorizer finished')

    print('Saving Vectorizer in pickle: ', os.path.join(
        args.model_dir, "vectorizer-ngram-(1,2).pickle"))
    file = open(os.path.join(args.model_dir,
                             "vectorizer-ngram-(1,2).pickle"), 'wb')
    pickle.dump(vectorizer, file)
    file.close()
    print('Vectorizer saved: ', os.path.join(
        args.model_dir, "vectorizer-ngram-(1,2).pickle"))

    # Vectorizing test_text and train_text
    train_text = vectorizer.transform(train_text)
    test_text = vectorizer.transform(test_text)
    print('Starting LogisticRegression training')
    LRmodel = LogisticRegression()
    print('Starting LogisticRegression fit')
    LRmodel.fit(X=train_text, y=train_sentiment)
    prediction = LRmodel.predict(test_text)
    print('Accuracy:', accuracy_score(test_sentiment, prediction))
    print('F1:', f1_score(test_sentiment, prediction))
    print('Confusion Matrix:', confusion_matrix(test_sentiment, prediction))
    print('Precision:', precision_score(test_sentiment, prediction))
    print('Recall Score:', recall_score(test_sentiment, prediction))
    print("Score:", LRmodel.score(test_text, test_sentiment))

    # Print the coefficients of the trained classifier, and save the coefficients
    joblib.dump(LRmodel, os.path.join(args.model_dir, "modelLR.joblib"))


def model_fn(model_dir):
    """Deserialized and return fitted model

    Note that this should have the same name as the serialized model in the main method
    """
    classifierMLP = joblib.load(os.path.join(model_dir, "modelLR.joblib"))
    return classifierMLP


def _npy_loads(data):
    """
    Deserializes npy-formatted bytes into a numpy array
    """
    stream = BytesIO(data)
    return np.load(stream)


def input_fn(input_data, content_type):
    """Parse input data payload

    We currently only take csv input. Since we need to process both labelled
    and unlabelled data we first determine whether the label column is present
    by looking at how many columns were provided.
    """
    print('Opening Vectorizer from local path: ', os.path.join(
        "/opt/ml/model", "vectorizer-ngram-(1,2).pickle"))
    file = open(os.path.join("/opt/ml/model",
                             "vectorizer-ngram-(1,2).pickle"), 'rb')
    vectorizer = pickle.load(file)
    file.close()

    if content_type == 'text/csv':
        # Read the raw input data as CSV.
        input_data = input_data.split('\r\n')
        print(f'Original Input: {input_data}')
        input_data = preprocess(input_data)
        print(f'Processed Input: {input_data}')
        input_data = vectorizer.transform(input_data)

        return input_data
    elif content_type == 'application/json':
        data = json.loads(input_data)
        print('Original Input:', data['sentiments'])
        input_sentiments = preprocess(data['sentiments'])
        print('Processed Input:', input_sentiments)
        data = vectorizer.transform(input_sentiments)

        return data
    elif content_type == 'application/x-npy':
        return _npy_loads(input_data)
    else:
        raise ValueError("{} not supported by script!".format(content_type))


def output_fn(prediction, accept):
    """Format prediction output

    The default accept/content-type between containers for serial inference is JSON.
    We also want to set the ContentType or mimetype as the same value as accept so the next
    container can read the response payload correctly.
    """
    print('Prediction: ', prediction)
    if accept == "application/json":
        predictions = []
        for row in prediction.tolist():
            if row[0] > 0.50:
                result = {"prediction": "Negative Sentiment",
                          "probability": row[0]}
            else:
                result = {"prediction": "Positive Sentiment",
                          "probability": row[1]}

            predictions.append(result)

        json_output = {"predictions": predictions}

        return worker.Response(json.dumps(json_output), accept, mimetype=accept)
    elif accept == 'text/csv':
        predictions = []
        for row in prediction.tolist():
            if row[0] > 0.50:
                result = f'Negative Sentiment. Probability: {row[0]}'
            else:
                result = f'Positive Sentiment. Probability: {row[1]}'
            print(f'Result:{result}')
            predictions.append(result)

        return worker.Response(encoders.encode(predictions, accept), accept, mimetype=accept)
    elif accept == 'application/x-npy':
        return _npy_loads(prediction)
    else:
        raise RuntimeException(
            "{} accept type is not supported by this script.".format(accept))


def predict_fn(input_data, model):
    print('Text to predict', input_data)
    sentiment = model.predict_proba(input_data)
    print('Sentiment', sentiment)

    return sentiment


"""
textdata: [string] => collection of sentences to be preprocessed
"""


def preprocess(textdata):
    processed_text = []

    # Defining regex patterns.
    url_pattern = r"((http://)[^ ]*|(https://)[^ ]*|( www\.)[^ ]*)"
    user_pattern = '@[^\s]+'
    alpha_pattern = "[^a-zA-Z0-9]"
    sequence_pattern = r"(.)\1\1+"
    seq_replace_pattern = r"\1\1"
    emojis = {':)': 'smile', ':-)': 'smile', ';d': 'wink', ':-E': 'vampire', ':(': 'sad',
              ':-(': 'sad', ':-<': 'sad', ':P': 'raspberry', ':O': 'surprised',
              ':-@': 'shocked', ':@': 'shocked', ':-$': 'confused', ':\\': 'annoyed',
              ':#': 'mute', ':X': 'mute', ':^)': 'smile', ':-&': 'confused', '$_$': 'greedy',
              '@@': 'eyeroll', ':-!': 'confused', ':-D': 'smile', ':-0': 'yell', 'O.o': 'confused',
              '<(-_-)>': 'robot', 'd[-_-]b': 'dj', ":'-)": 'sadsmile', ';)': 'wink',
              ';-)': 'wink', 'O:-)': 'angel', 'O*-)': 'angel', '(:-D': 'gossip', '=^.^=': 'cat',
              '&lt;3': 'heart', '<3': 'heart'}

    for i in range(len(textdata)):
        tweet = textdata[i]
        # Lower casing
        tweet = tweet.lower()

        # Remove all URls
        tweet = re.sub(url_pattern, '', tweet)

        # Replace all emojis.
        for emoji in emojis.keys():
            tweet = tweet.replace(emoji, " EMOJI" + emojis[emoji])

        # Replace @USERNAME to ' '.
        tweet = re.sub(user_pattern, ' ', tweet)

        # Remove word &quot; &amp; &gt; &lt; and others
        tweet = unescape(tweet)

        # Replace all non alphabets.
        tweet = re.sub(alpha_pattern, " ", tweet)
        # Replace 3 or more consecutive letters by 2 letter.
        tweet = re.sub(sequence_pattern, seq_replace_pattern, tweet)

        word_tokens = word_tokenize(tweet)
        sentence = ' '.join(word_tokens)
        processed_text.append(sentence)

    return processed_text
