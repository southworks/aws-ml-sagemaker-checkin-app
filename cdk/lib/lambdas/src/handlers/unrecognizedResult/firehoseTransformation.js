'use strict';
console.log('Loading function');

exports.handler = (event, context, callback) => {

  /* Process the list of records and transform them */
  const output = event.records.map((record) => {

    const entry = (Buffer.from(record.data, 'base64')).toString('utf8');
    console.log(entry);

    let parsed_entry = JSON.parse(entry);

    const result = `_label_0or1 ${parsed_entry.inputText}` + "\n";
    const payload = (Buffer.from(result, 'utf8')).toString('base64');

    return {
      recordId: record.recordId,
      result: 'Ok',
      data: payload,
    };

  });
  console.log(`Processing completed.  Successful records ${output.length}.`);
  callback(null, { records: output });
};
