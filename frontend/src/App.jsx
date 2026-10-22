
import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [verifyingId, setVerifyingId] = useState(null);
  const [normalizingId, setNormalizingId] = useState(null);
  const [interactionResult, setInteractionResult] = useState(null);
  const [checkingInteractions, setCheckingInteractions] =
    useState(false);
     const [riskResult, setRiskResult] = useState(null);
const [checkingRisks, setCheckingRisks] = useState(false);
const [reportResult, setReportResult] = useState(null);
const [loadingReport, setLoadingReport] = useState(false);

  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    const file = event.target.files[0];

   

    if (!file) {
      return;
    }

    setSelectedFile(file);
    setUploadResult(null);
    setMedicines([]);
    setInteractionResult(null);
    setError("");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Please select a prescription image first.");
      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("image", selectedFile);

    try {
      const response = await axios.post(
        "/api/prescriptions/upload/",
        formData
      );

      setUploadResult(response.data);

      setMedicines(
        response.data.medicines.map((medicine) => ({
          ...medicine,
          verifiedName:
            medicine.verified_name ||
            medicine.medicine_text,
          verified:
            medicine.verified || false,
          normalizationStatus:
            medicine.normalization_status || "pending",
          rxnormName:
            medicine.rxnorm_name || null,
          rxcui:
            medicine.rxnorm_rxcui || null,
        }))
      );

      setInteractionResult(null);
    } catch (uploadError) {
      console.error(uploadError);

      setError(
        "Unable to analyze the prescription. Please make sure Django is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleMedicineNameChange = (
    medicineIndex,
    value
  ) => {
    setMedicines((currentMedicines) =>
      currentMedicines.map((medicine, index) =>
        index === medicineIndex
          ? {
              ...medicine,
              verifiedName: value,
              normalizationStatus: "pending",
              rxnormName: null,
              rxcui: null,
            }
          : medicine
      )
    );

    setInteractionResult(null);
  };

  const handleVerify = async (
    medicine,
    medicineIndex
  ) => {
    if (!medicine.verifiedName.trim()) {
      setError("Medicine name cannot be empty.");
      return;
    }

    setVerifyingId(medicine.id);
    setError("");

    try {
      const response = await axios.patch(
        `/api/prescriptions/medicines/${medicine.id}/verify/`,
        {
          verified: true,
          verified_name:
            medicine.verifiedName.trim(),
        }
      );

      setMedicines((currentMedicines) =>
        currentMedicines.map((item, index) =>
          index === medicineIndex
            ? {
                ...item,
                verified:
                  response.data.verified,
                verifiedName:
                  response.data.verified_name,
                normalizationStatus: "pending",
                rxnormName: null,
                rxcui: null,
              }
            : item
        )
      );

      setInteractionResult(null);
    } catch (verificationError) {
      console.error(verificationError);

      setError(
        "Unable to verify this medicine. Please check that Django is running."
      );
    } finally {
      setVerifyingId(null);
    }
  };

  const handleEdit = (medicineIndex) => {
    setMedicines((currentMedicines) =>
      currentMedicines.map((medicine, index) =>
        index === medicineIndex
          ? {
              ...medicine,
              verified: false,
              normalizationStatus: "pending",
              rxnormName: null,
              rxcui: null,
            }
          : medicine
      )
    );

    setInteractionResult(null);
    setError("");
  };

 const handleNormalize = async (
  medicine,
  medicineIndex
) => {
  setNormalizingId(medicine.id);
  setError("");

  try {
    const response = await axios.post(
      `/api/prescriptions/medicines/${medicine.id}/normalize/`
    );

    setMedicines((currentMedicines) =>
      currentMedicines.map((item, index) =>
        index === medicineIndex
          ? {
              ...item,
              normalizationStatus:
                response.data.status,
              rxnormName:
                response.data.name ||
                response.data.rxnorm_name ||
                null,
              rxcui:
                response.data.rxcui ||
                response.data.rxnorm_rxcui ||
                null,
            }
          : item
      )
    );

    if (response.data.status === "normalized") {
      setError("");
    }

  } catch (error) {
    if (error.response?.status === 422) {
      const data = error.response.data;

      setMedicines((currentMedicines) =>
        currentMedicines.map((item, index) =>
          index === medicineIndex
            ? {
                ...item,
                normalizationStatus:
                  "needs_review",
                rxnormName: null,
                rxcui: null,
              }
            : item
        )
      );

      setError(
        data.reason ||
        "RxNorm could not confidently identify this medicine. Please review the medicine name."
      );

    } else if (error.response?.status === 400) {
      setError(
        error.response.data?.reason ||
        "This medicine must be verified before normalization."
      );

    } else {
      setError(
        "Something went wrong while normalizing the medicine."
      );
    }

  } finally {
    setNormalizingId(null);
  }
};

const handleRiskAnalysis = async () => {
  const prescriptionId =
    uploadResult?.prescription_id ||
    uploadResult?.id;

  if (!prescriptionId) {
    setError("Prescription ID is missing.");
    return;
  }

  setCheckingRisks(true);
  setError("");
  setRiskResult(null);

  try {
    const response = await axios.get(
      `/api/prescriptions/${prescriptionId}/risk-analysis/`
    );

    console.log(
      "RISK ANALYSIS RESPONSE:",
      response.data
    );

    setRiskResult(response.data);

  } catch (riskError) {
    console.error(
      "RISK ANALYSIS ERROR:",
      riskError.response?.data ||
      riskError
    );

    setError(
      "Unable to analyze patient safety risks."
    );

  } finally {
    setCheckingRisks(false);
  }
};

const handleGenerateReport = async () => {
  const prescriptionId =
    uploadResult?.prescription_id ||
    uploadResult?.id;

  if (!prescriptionId) {
    setError("Prescription ID is missing.");
    return;
  }

  setLoadingReport(true);
  setError("");
  setReportResult(null);

  try {
    const response = await axios.get(
      `/api/prescriptions/${prescriptionId}/report/`
    );

    console.log(
      "REPORT RESPONSE:",
      response.data
    );

    setReportResult(response.data);

  } catch (reportError) {
    console.error(
      "REPORT ERROR:",
      reportError.response?.data ||
      reportError
    );

    setError(
      "Unable to generate the final report."
    );

  } finally {
    setLoadingReport(false);
  }
};

  const verifiedCount = medicines.filter(
    (medicine) => medicine.verified
  ).length;

  const normalizedCount = medicines.filter(
    (medicine) =>
      medicine.normalizationStatus ===
      "normalized"
  ).length;

  const allMedicinesNormalized =
    medicines.length > 0 &&
    normalizedCount === medicines.length;

  return (
    <div className="app">
      <header className="navbar">
        <div>
          <h1>Polypharmacy Crisis</h1>
          <p>
            Medication safety decision support
          </p>
        </div>

        <div className="status-badge">
          <span className="status-dot"></span>
          System Ready
        </div>
      </header>

      <main className="main-content">
        <section className="hero">
          <div>
            <p className="eyebrow">
              MEDICATION SAFETY
            </p>

            <h2>
              Detect medication risks
              <br />
              before they become problems.
            </h2>

            <p className="hero-text">
              Upload a prescription to extract
              medicines, verify them, normalize
              drug identities, and identify
              potential medication safety concerns.
            </p>
          </div>
        </section>

        <section className="upload-card">
          <div className="upload-header">
            <div>
              <p className="section-label">
                STEP 01
              </p>

              <h3>Upload prescription</h3>
            </div>

            <div className="upload-icon">
              +
            </div>
          </div>

          <label className="drop-zone">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
            />

            <div className="upload-symbol">
              ↑
            </div>

            <strong>
              {selectedFile
                ? selectedFile.name
                : "Choose prescription image"}
            </strong>

            <span>
              PNG, JPG or JPEG
            </span>
          </label>

          {selectedFile && (
            <div className="selected-file">
              <span>Selected</span>

              <strong>
                {selectedFile.name}
              </strong>
            </div>
          )}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <button
            className="analyze-button"
            onClick={handleUpload}
            disabled={loading}
          >
            {loading
              ? "Analyzing..."
              : "Analyze Prescription →"}
          </button>
        </section>

        {uploadResult && (
          <section className="verification-card">
            <div className="result-header">
              <div>
                <p className="section-label">
                  STEP 02
                </p>

                <h3>
                  Verify & normalize medicines
                </h3>
              </div>

              <div className="verification-progress">
                {verifiedCount}/{medicines.length}{" "}
                verified
              </div>
            </div>

            <div className="verification-note">
              <strong>
                Why verification?
              </strong>

              <p>
                OCR can misread prescription text.
                Review and correct each extracted
                medicine before RxNorm normalization
                and risk analysis.
              </p>
            </div>

            <div className="medicine-list">
              {medicines.map(
                (medicine, index) => (
                  <div
                    className="verification-row"
                    key={
                      medicine.id || index
                    }
                  >
                    <div className="medicine-number">
                      {String(index + 1).padStart(
                        2,
                        "0"
                      )}
                    </div>

                    <div className="medicine-details">
                      <div className="medicine-top">
                        <span className="medicine-label">
                          OCR detected
                        </span>

                        <span className="confidence">
                          {Math.round(
                            medicine.confidence *
                              100
                          )}
                          % confidence
                        </span>
                      </div>

                      <strong className="ocr-name">
                        {medicine.medicine_text}
                      </strong>

                      <label className="verified-label">
                        Verified medicine name

                        <input
                          type="text"
                          value={
                            medicine.verifiedName
                          }
                          onChange={(event) =>
                            handleMedicineNameChange(
                              index,
                              event.target.value
                            )
                          }
                        />
                      </label>

                      <div className="verification-actions">
                        {!medicine.verified ? (
                          <button
                            className="verify-button"
                            onClick={() =>
                              handleVerify(
                                medicine,
                                index
                              )
                            }
                            disabled={
                              verifyingId ===
                              medicine.id
                            }
                          >
                            {verifyingId ===
                            medicine.id
                              ? "Saving..."
                              : "Verify Medicine"}
                          </button>
                        ) : (
                          <div className="verified-actions">
                            <div className="verified-status">
                              ✓ Verified
                            </div>

                            <button
                              className="edit-button"
                              onClick={() =>
                                handleEdit(index)
                              }
                            >
                              Edit
                            </button>
                          </div>
                        )}
                      </div>

                      {medicine.verified && (
                        <div className="normalization-section">
                          {medicine.normalizationStatus ===
                          "normalized" ? (
                            <div className="normalized-result">
                              <div className="normalized-header">
                                <span className="normalized-status">
                                  ✓ RxNorm Normalized
                                </span>
                              </div>

                              <strong>
                                {
                                  medicine.rxnormName
                                }
                              </strong>

                              <span>
                                RxCUI:{" "}
                                {medicine.rxcui}
                              </span>
                            </div>
                          ) : (
                            <button
                              className="normalize-button"
                              onClick={() =>
                                handleNormalize(
                                  medicine,
                                  index
                                )
                              }
                              disabled={
                                normalizingId ===
                                medicine.id
                              }
                            >
                              {normalizingId ===
                              medicine.id
                                ? "Normalizing..."
                                : "Normalize with RxNorm →"}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              )}
            </div>
          </section>
        )}

        {allMedicinesNormalized && (
          <section className="next-step-card">
            <div>
              <p className="section-label">
                STEP 03
              </p>

              <h3>
                Check medication interactions
              </h3>

              <p>
                All verified medicines have been
                normalized with RxNorm. The system
                can now compare the medications and
                look for evidence of potential
                interactions.
              </p>
            </div>

            {!interactionResult ? (
              <button
                className="interaction-button"
                onClick={handleCheckInteractions}
                disabled={checkingInteractions}
              >
                {checkingInteractions
                  ? "Checking..."
                  : "Check for interactions →"}
              </button>
            ) : (
              <div className="interaction-complete">
                ✓ Analysis Complete
              </div>
            )}
          </section>
        )}

        {interactionResult && (
  <section className="next-step-card">
    <div className="next-step-header">
      <div>
        <p className="section-label">
          STEP 04
        </p>

        <h3>
          Patient safety analysis
        </h3>

        <p>
          Check the verified medicines against
          the available patient context.
        </p>
      </div>
    </div>

    {!riskResult ? (
      <button
        className="interaction-button"
        onClick={handleRiskAnalysis}
        disabled={checkingRisks}
      >
        {checkingRisks
          ? "Analyzing..."
          : "Analyze patient risks →"}
      </button>
    ) : (
      <div className="interaction-complete">
        ✓ Risk Analysis Complete
      </div>
    )}
  </section>
)}

{riskResult && (
  <section className="interaction-result-card">
    <div className="result-header">
      <div>
        <p className="section-label">
          PATIENT SAFETY ANALYSIS
        </p>

        <h3>
          Risk findings
        </h3>
      </div>

      <div className="interaction-count">
        {riskResult.total_findings || 0} found
      </div>
    </div>

    {riskResult.findings?.length > 0 ? (
      <div className="interaction-list">
        {riskResult.findings.map(
          (finding, index) => (
            <div
              className="interaction-item"
              key={index}
            >
              <div className="interaction-medicines">
                <strong>
                  {finding.type === "allergy"
                    ? "Allergy"
                    : finding.type ===
                        "drug_interaction"
                      ? "Drug Interaction"
                      : finding.type}
                </strong>

                <span>
                  {finding.severity ||
                    "Needs review"}
                </span>
              </div>

              {finding.type ===
                "drug_interaction" && (
                <p>
                  <strong>
                    {finding.medicine_a}
                  </strong>

                  {" + "}

                  <strong>
                    {finding.medicine_b}
                  </strong>
                </p>
              )}

              {finding.type === "allergy" && (
                <p>
                  <strong>
                    {finding.medicine}
                  </strong>
                </p>
              )}

              <p>
                {finding.message}
              </p>

              {finding.source && (
                <span className="interaction-source">
                  Source: {finding.source}
                </span>
              )}
            </div>
          )
        )}
      </div>
    ) : (
      <div className="no-interactions">
        <strong>
          No risk findings identified
        </strong>

        <p>
          No findings were generated from the
          available patient context and normalized
          medicines.
        </p>
      </div>
    )}
  </section>
)}

{riskResult && (
  <section className="next-step-card">
    <div className="next-step-header">
      <div>
        <p className="section-label">
          STEP 05
        </p>

        <h3>
          Final safety report
        </h3>

        <p>
          Generate a consolidated report containing
          the verified medicines, interactions,
          patient context, and risk findings.
        </p>
      </div>
    </div>

    {!reportResult ? (
      <button
        className="interaction-button"
        onClick={handleGenerateReport}
        disabled={loadingReport}
      >
        {loadingReport
          ? "Generating report..."
          : "Generate Final Report →"}
      </button>
    ) : (
      <div className="interaction-complete">
        ✓ Final Report Generated
      </div>
    )}
  </section>
)}
     {reportResult && (
  <section className="interaction-result-card">
    <div className="result-header">
      <div>
        <p className="section-label">
          FINAL REPORT
        </p>

        <h3>
          Medication safety report
        </h3>
      </div>

      <div className="interaction-count">
        {reportResult.summary?.total_risk_findings || 0} findings
      </div>
    </div>

    <div className="report-summary-grid">
      <div className="report-summary-item">
        <span>Total medicines</span>
        <strong>
          {reportResult.summary?.total_medicines || 0}
        </strong>
      </div>

      <div className="report-summary-item">
        <span>Verified</span>
        <strong>
          {reportResult.summary?.verified_medicines || 0}
        </strong>
      </div>

      <div className="report-summary-item">
        <span>Normalized</span>
        <strong>
          {reportResult.summary?.normalized_medicines || 0}
        </strong>
      </div>

      <div className="report-summary-item">
        <span>Interactions</span>
        <strong>
          {reportResult.summary?.interactions_found || 0}
        </strong>
      </div>
    </div>

    {reportResult.patient && (
      <div className="report-section">
        <p className="section-label">
          PATIENT CONTEXT
        </p>

        <h4>
          Patient information
        </h4>

        <p>
          <strong>Age:</strong>{" "}
          {reportResult.patient.age}
        </p>

        <p>
          <strong>Allergies:</strong>{" "}
          {reportResult.patient.allergies ||
            "None provided"}
        </p>

        <p>
          <strong>Conditions:</strong>{" "}
          {reportResult.patient.conditions ||
            "None provided"}
        </p>

        <p>
          <strong>Current medications:</strong>{" "}
          {reportResult.patient.current_medications ||
            "None provided"}
        </p>
      </div>
    )}

    <div className="report-section">
      <p className="section-label">
        MEDICINES
      </p>

      <h4>
        Verified medications
      </h4>

      <div className="interaction-list">
        {reportResult.medicines?.map(
          (medicine) => (
            <div
              className="interaction-item"
              key={medicine.id}
            >
              <strong>
                {medicine.verified_name ||
                  medicine.medicine_text}
              </strong>

              <p>
                RxNorm:{" "}
                {medicine.rxnorm_name ||
                  "Not normalized"}
              </p>

              {medicine.rxnorm_rxcui && (
                <span className="interaction-source">
                  RxCUI: {medicine.rxnorm_rxcui}
                </span>
              )}
            </div>
          )
        )}
      </div>
    </div>

    <div className="report-section">
      <p className="section-label">
        RISK FINDINGS
      </p>

      <h4>
        Patient safety findings
      </h4>

      {reportResult.summary?.risk_findings?.length > 0 ? (
        <div className="interaction-list">
          {reportResult.summary.risk_findings.map(
            (finding, index) => (
              <div
                className="interaction-item"
                key={index}
              >
                <div className="interaction-medicines">
                  <strong>
                    {finding.type === "allergy"
                      ? "Allergy"
                      : finding.type ===
                          "drug_interaction"
                        ? "Drug Interaction"
                        : finding.type}
                  </strong>

                  <span>
                    {finding.severity ||
                      "Needs review"}
                  </span>
                </div>

                {finding.type ===
                  "drug_interaction" && (
                  <p>
                    <strong>
                      {finding.medicine_a}
                    </strong>
                    {" + "}
                    <strong>
                      {finding.medicine_b}
                    </strong>
                  </p>
                )}

                {finding.medicine && (
                  <p>
                    <strong>
                      {finding.medicine}
                    </strong>
                  </p>
                )}

                <p>
                  {finding.message}
                </p>

                {finding.source && (
                  <span className="interaction-source">
                    Source: {finding.source}
                  </span>
                )}
              </div>
            )
          )}
        </div>
      ) : (
        <div className="no-interactions">
          <strong>
            No risk findings identified
          </strong>

          <p>
            No findings were generated from the
            available patient context and
            normalized medicines.
          </p>
        </div>
      )}
    </div>
  </section>
)}
        {interactionResult && (
  <section className="interaction-result-card">
    <div className="result-header">
      <div>
        <p className="section-label">
          INTERACTION ANALYSIS
        </p>

        <h3>
          Medication interaction results
        </h3>
      </div>

      <div className="interaction-count">
        {interactionResult.results?.filter(
          (result) =>
            result.status === "interaction_saved" ||
            result.status === "already_exists"
        ).length || 0}{" "}
        found
      </div>
    </div>

    {interactionResult.results?.filter(
      (result) =>
        result.status === "interaction_saved" ||
        result.status === "already_exists"
    ).length > 0 ? (
      <div className="interaction-list">
        {interactionResult.results
          .filter(
            (result) =>
              result.status === "interaction_saved" ||
              result.status === "already_exists"
          )
          .map((interaction, index) => (
            <div
              className="interaction-item"
              key={
                interaction.interaction_id ||
                index
              }
            >
              <div className="interaction-medicines">
                <strong>
                  {interaction.medicine_a}
                </strong>

                <span>+</span>

                <strong>
                  {interaction.medicine_b}
                </strong>
              </div>

              <div className="interaction-severity">
                {interaction.severity ||
                  "Potential interaction"}
              </div>

              <p>
                {interaction.description ||
                  "Potential interaction identified between these medicines."}
              </p>

              {interaction.source && (
                <span className="interaction-source">
                  Source: {interaction.source}
                </span>
              )}
            </div>
          ))}
      </div>
    ) : (
      <div className="no-interactions">
        <strong>
          No interaction evidence found
        </strong>

        <p>
          No interaction evidence was identified
          for the normalized medicine pairs checked
          by the current evidence engine.
        </p>
      </div>
    )}
  </section>
)}
      </main>

      <footer>
        <span>
          Polypharmacy Crisis
        </span>

        <span>
          Decision-support prototype · Not a
          diagnostic tool
        </span>
      </footer>
    </div>
  );
}

export default App;

