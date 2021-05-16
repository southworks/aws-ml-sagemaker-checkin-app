export const imageContainer = (() => {
  const imageContainer = new Map();
  imageContainer.set(
    "blazingText",
    "811284229777.dkr.ecr.us-east-1.amazonaws.com/blazingtext:1"
  );
  imageContainer.set(
    "chainer",
    "520713654638.dkr.ecr.us-east-1.amazonaws.com/sagemaker-chainer:5.0.0-cpu-py3"
  );

  return imageContainer;
})();
