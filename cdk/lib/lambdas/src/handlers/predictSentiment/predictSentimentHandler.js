const AWS = require("aws-sdk");
const config = require("./../../config.json");

const createMessage = (prediction, event, uuid) => {
  var response = {
    ...event,
  };
  response.id = uuid;
  response.label = prediction.label[0];
  response.prob = prediction.prob[0];

  if (response.prob < config.aws.SageMaker.predictionProbabilityThreshold) {
    response.sentiment = "UNRECOGNIZED";
  } else if (response.label === config.aws.SageMaker.negativeLabel) {
    response.sentiment = "NEGATIVE";
  } else if (response.label === config.aws.SageMaker.positiveLabel) {
    response.sentiment = "POSITIVE";
  } else {
    response.sentiment = "UNRECOGNIZED";
  }

  console.log(
    "Threshold: " + config.aws.SageMaker.predictionProbabilityThreshold
  );
  console.log("Likelihood: " + response.prob);
  console.log("Prediction:" + response.sentiment);
  return response;
};

exports.handler = async (event, context) => {
  var request = {
    instances: [event.inputText],
  };

  var params = {
    Body: JSON.stringify(request),
    EndpointName: config.aws.SageMaker.endpointName,
    Accept: "application/json",
    ContentType: "application/json",
  };

  var sagemaker = new AWS.SageMakerRuntime();

  var response = await sagemaker.invokeEndpoint(params).promise();
  var prediction = JSON.parse(response.Body.toString())[0];

  return createMessage(prediction, event, context.awsRequestId);
};
