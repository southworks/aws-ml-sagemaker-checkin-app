const AWS = require("aws-sdk");
const bucketS3 = require("@aws-cdk/aws-s3");
const s3Assets = require("@aws-cdk/aws-s3-assets");
const s3 = new AWS.S3();
const Path = require("path");

const exists = async (bucket) => {
  const options = {
    Bucket: bucket.name,
  };
  try {
    await s3.headBucket(options).promise();
    return true;
  } catch (error) {
    if (error.statusCode === 404) {
      return false;
    }
    throw error;
  }
};

const createBucket = async (stack, bucket) => {
  console.log(bucket);
  if (!(await exists(bucket))) {
    console.log(`${bucket.name} BUCKET DOESN'T EXISTS`);
    const buckS3 = new bucketS3.Bucket(stack, bucket.name, {
      bucketName: bucket.name,
    });
    return buckS3;
  } else {
    console.log(`${bucket.name} BUCKET EXISTS`);
  }
};

const assetsUpload = (stack, assetPaths) => {
  const objectUrls = {};

  for (const [assetKey, assetPath] of Object.entries(assetPaths)) {
    objectUrls[assetKey] = new s3Assets.Asset(stack, `S3Asset${assetKey}`, {
      path: Path.join(__dirname, assetPath),
    });
  }
  return objectUrls;
};

module.exports = {
  exists,
  createBucket,
  assetsUpload,
};
