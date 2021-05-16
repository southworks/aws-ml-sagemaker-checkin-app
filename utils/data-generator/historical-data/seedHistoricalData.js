const config = require("../config.json");
const casual = require("casual").en_US;
const producer = require("./persistence/kdsProducer");
const countries = require("./countryCoordinates.json");

class SeedHistoricalData {
  constructor() {
    let earliestRecordDate = new Date();
    earliestRecordDate.setDate(
      earliestRecordDate.getDate() - config.daysToGenerate
    );
    let greatestRecordDate = new Date();
    let earliestEpoch = Math.trunc(earliestRecordDate.getTime() / 1000);
    let greatestEpoch = Math.trunc(greatestRecordDate.getTime() / 1000);

    this.records = config.dailyRecordsPerUser * config.daysToGenerate;

    this.kdsProducer = new producer();

    casual.define("place", function (administratorId) {
      let place = casual.random_element(countries);
      return {
        country: place.country,
        longitude: place.longitude,
        latitude: place.latitude,
      };
    });

    casual.define("feeling", function (userId, place) {
      return {
        id: casual.uuid,
        dateTime: casual.integer(earliestEpoch, greatestEpoch),
        audioUrl: "http://",
        inputText: casual.sentence,
        sentiment: casual.random_element([
          "POSITIVE",
          "NEGATIVE",
          "UNRECOGNIZED",
        ]),
        label: "seed",
        probability: 0.99,
        userId: userId,
        location: {
          country: place.country,
          latitude: place.latitude,
          longitude: place.longitude,
        },
      };
    });
  }

  generateHistoricalData(usersArray) {
    usersArray.forEach((user) => {
      let randFlag = false;
      let randTracker = 1;
      let randSet = 0;
      let currentFeeling = "";
      let place = casual.place(null);
      for (let i = 0; i < this.records; i++) {
        if (casual.integer(0, 2) == 2) {
          place = casual.place();
        }
        let feeling = casual.feeling(user.id, place);
        if (!randFlag) {
          currentFeeling = feeling.sentiment;
          randSet = this.generateRandSet(currentFeeling);
          randFlag = true;
        } else {
          feeling.sentiment = currentFeeling;
          randTracker++;
          if (randTracker == randSet) {
            randTracker = 1;
            randFlag = false;
          }
        }
        feeling = JSON.stringify(feeling) + "\n";
        console.log("FEELING: ", feeling);
        this.kdsProducer.persist(feeling);
      }
    });
  }

  generateRandSet(intentName) {
    switch (intentName) {
    case "POSITIVE":
      return casual.integer(config.dailyRecordsPerUser, this.records);
    case "NEGATIVE":
      return casual.integer(2, 3 + config.dailyRecordsPerUser);
    case "UNRECOGNIZED":
      return casual.integer(
        config.dailyRecordsPerUser,
        config.dailyRecordsPerUser + config.dailyRecordsPerUser / 2
      );
    default:
      return config.dailyRecordsPerUser;
    }
  }
}

module.exports = SeedHistoricalData;
