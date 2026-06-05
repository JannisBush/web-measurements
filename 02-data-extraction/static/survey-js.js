// @ts-check
/// <reference path="survey.d.ts" />
/**
 * @typedef {import("survey-core").Model} SurveyModel
*/

let CURRENT_PAPER_ID = null;
let CURRENT_EXTRACTOR = null;
const PAPER_DETAILS_ENDPOINT = "/get_paper_details";
const SAVE_INTERMEDIATE = "/save_progress";
const LOAD_INTERMEDIATE = "/get_progress";
const SAVE_FINAL = "/submit";


/** @param {SurveyModel} survey */
function saveSurveyData(survey) {
  const data = survey.data;
  data.pageNo = survey.currentPageNo;

  // console.log(survey.data);

  let extractor_name = data["1-q-p0-name"];
  let paper_id = data["3-q-p0-paperselect"];
  if (extractor_name && paper_id) {
    if (extractor_name != CURRENT_EXTRACTOR || paper_id != CURRENT_PAPER_ID) {
      CURRENT_EXTRACTOR = extractor_name;
      CURRENT_PAPER_ID = paper_id;
      console.log(extractor_name, paper_id);
      // Load paper config data
      fetch(`${PAPER_DETAILS_ENDPOINT}?id=${CURRENT_PAPER_ID}`).then(data => data.json()).then(data => {
        // console.log(data);
        survey.setValue("4-q-p1-meta-1-metadata", data);
        let pdf_field = survey.getQuestionByName("7-q-p1-meta-1-pdf")
        pdf_field.html = `<a href=/static/pdf/${data["pdf_path"]} target="_blank">Open paper in new tab</a> <a href=/static/pdf/${data["pdf_path"]} download>Download paper</a>`;
      })
      // (Optional) restore survey data
      restoreSurveyData(survey);
      return; // Do not save the data (could overwrite the restored one due to race condition)
    }
  }
  // Save data
  if (CURRENT_EXTRACTOR && CURRENT_PAPER_ID) {
    fetch(`${SAVE_INTERMEDIATE}?extractor=${CURRENT_EXTRACTOR}&paper_id=${CURRENT_PAPER_ID}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(response => response.json())
      //.then(data => console.log(data))
      .catch(error => console.error(error));
  }
}

/** @param {SurveyModel} survey */
function restoreSurveyData(survey) {
  fetch(`${LOAD_INTERMEDIATE}?extractor=${CURRENT_EXTRACTOR}&paper_id=${CURRENT_PAPER_ID}`).then(data => data.json()).then(
    data => {
      if (data["error"]) {
        console.log(data);
      } else {
        console.log("Successfully restored data");
        survey.data = data;
      }
    }
  )
}

document.addEventListener("DOMContentLoaded", function () {

  fetch("/schema")
    .then(response => response.json())
    .then(json => {
      const survey = new Survey.Model(json);

      // Intermediate saving of data
      survey.onValueChanged.add(saveSurveyData);
      survey.onCurrentPageChanged.add(saveSurveyData);

      // Save the results
      survey.onComplete.add(result => {
        console.log(result.data);
        fetch(SAVE_FINAL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(result.data)
        }).then(r => {
          if (r.ok) {
            alert("Thank you!");
          }
          else {
            alert("Submission failed.");
          };
        });
      });

      // Display the survey
      const surveyContainer = document.getElementById("surveyContainer");
      survey.render(surveyContainer);
    });
});
