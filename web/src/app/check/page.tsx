"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import FileUpload from "@/components/FileUpload";
import UniversitySelect from "@/components/UniversitySelect";
import ComplianceReportComponent from "@/components/ComplianceReport";
import type { SpecInfo, ComplianceReport, CheckResponse } from "@/lib/types";
import { transformCheckResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type CheckStep = "upload" | "analyzing" | "results";

export default function CheckPage() {
  const [step, setStep] = useState<CheckStep>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [specs, setSpecs] = useState<SpecInfo[]>([]);
  const [selectedSpec, setSelectedSpec] = useState<SpecInfo | null>(null);
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch available specs from Python API on mount
  useEffect(() => {
    async function fetchSpecs() {
      try {
        const response = await fetch(`${API_BASE_URL}/specs`);
        if (!response.ok) {
          throw new Error("Failed to fetch specifications");
        }
        const data: SpecInfo[] = await response.json();
        setSpecs(data);
      } catch (err) {
        setError("Failed to connect to the server. Please ensure the backend is running.");
      } finally {
        setLoading(false);
      }
    }
    fetchSpecs();
  }, []);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleSpecSelect = (spec: SpecInfo) => {
    setSelectedSpec(spec);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile || !selectedSpec) {
      setError("Please upload a PDF and select your university.");
      return;
    }

    setStep("analyzing");
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("spec", selectedSpec.name);

      const response = await fetch(`${API_BASE_URL}/check`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to analyze PDF");
      }

      const checkResponse: CheckResponse = await response.json();
      const reportData = transformCheckResponse(checkResponse, selectedSpec.university);
      setReport(reportData);
      setStep("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setStep("upload");
    }
  };

  const handleReset = () => {
    setStep("upload");
    setSelectedFile(null);
    setSelectedSpec(null);
    setReport(null);
    setError(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto" />
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center space-x-2">
              <svg
                className="h-8 w-8 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="text-xl font-bold text-gray-900">
                ThesisCheck
              </span>
            </Link>
            {step !== "upload" && (
              <button
                onClick={handleReset}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Start Over
              </button>
            )}
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 py-12">
        {step === "upload" && (
          <>
            {/* Progress Indicator */}
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-4">
                <div className="flex items-center">
                  <span className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
                    1
                  </span>
                  <span className="ml-2 text-sm font-medium text-gray-900">
                    Upload & Select
                  </span>
                </div>
                <div className="w-16 h-0.5 bg-gray-300" />
                <div className="flex items-center">
                  <span className="w-8 h-8 rounded-full bg-gray-300 text-gray-500 flex items-center justify-center text-sm font-medium">
                    2
                  </span>
                  <span className="ml-2 text-sm font-medium text-gray-500">
                    Analyze
                  </span>
                </div>
                <div className="w-16 h-0.5 bg-gray-300" />
                <div className="flex items-center">
                  <span className="w-8 h-8 rounded-full bg-gray-300 text-gray-500 flex items-center justify-center text-sm font-medium">
                    3
                  </span>
                  <span className="ml-2 text-sm font-medium text-gray-500">
                    Results
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Check Your Thesis Formatting
              </h1>
              <p className="text-gray-600 mb-8">
                Upload your thesis PDF and select your university to get an
                instant compliance report.
              </p>

              <div className="space-y-8">
                {/* File Upload */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    1. Upload Your PDF
                  </h2>
                  <FileUpload onFileSelect={handleFileSelect} />
                </div>

                {/* University Selection */}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    2. Select Your University
                  </h2>
                  <UniversitySelect
                    specs={specs}
                    selectedName={selectedSpec?.name ?? null}
                    onSelect={handleSpecSelect}
                  />
                </div>

                {/* Error Message */}
                {error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex">
                      <svg
                        className="h-5 w-5 text-red-400"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <p className="ml-3 text-sm text-red-700">{error}</p>
                    </div>
                  </div>
                )}

                {/* Analyze Button */}
                <button
                  onClick={handleAnalyze}
                  disabled={!selectedFile || !selectedSpec}
                  className={`
                    w-full py-4 px-6 rounded-lg font-medium text-lg
                    transition-all duration-200
                    ${
                      selectedFile && selectedSpec
                        ? "bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/25"
                        : "bg-gray-200 text-gray-500 cursor-not-allowed"
                    }
                  `}
                >
                  {selectedFile && selectedSpec
                    ? "Check Compliance"
                    : "Upload PDF and Select University"}
                </button>
              </div>
            </div>
          </>
        )}

        {step === "analyzing" && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-600 border-t-transparent mx-auto" />
            <h2 className="mt-6 text-xl font-semibold text-gray-900">
              Analyzing Your Thesis
            </h2>
            <p className="mt-2 text-gray-600">
              Checking formatting against {selectedSpec?.university} requirements...
            </p>
            <div className="mt-8 space-y-3 text-left max-w-sm mx-auto">
              <div className="flex items-center text-sm text-gray-600">
                <svg
                  className="h-5 w-5 text-green-500 mr-3"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                Reading PDF document...
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <svg
                  className="h-5 w-5 text-blue-500 mr-3 animate-pulse"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
                Checking page dimensions...
              </div>
              <div className="flex items-center text-sm text-gray-500">
                <div className="h-5 w-5 mr-3" />
                Validating margins...
              </div>
              <div className="flex items-center text-sm text-gray-500">
                <div className="h-5 w-5 mr-3" />
                Generating report...
              </div>
            </div>
          </div>
        )}

        {step === "results" && report && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <ComplianceReportComponent report={report} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-8 mt-12">
        <div className="max-w-4xl mx-auto px-4 text-center text-sm text-gray-500">
          <p>
            ThesisCheck analyzes your PDF against known university formatting
            requirements. Always verify with your graduate school&apos;s official
            guidelines.
          </p>
        </div>
      </footer>
    </div>
  );
}
