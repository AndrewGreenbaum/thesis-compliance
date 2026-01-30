"use client";

import type { ComplianceReport as ReportType, DisplayViolation } from "@/lib/types";

interface ComplianceReportProps {
  report: ReportType;
}

function getSeverityStyles(severity: string) {
  switch (severity) {
    case "error":
      return {
        bg: "bg-red-50",
        border: "border-red-200",
        icon: "text-red-500",
        text: "text-red-800",
        badge: "bg-red-100 text-red-800",
      };
    case "warning":
      return {
        bg: "bg-yellow-50",
        border: "border-yellow-200",
        icon: "text-yellow-500",
        text: "text-yellow-800",
        badge: "bg-yellow-100 text-yellow-800",
      };
    default:
      return {
        bg: "bg-blue-50",
        border: "border-blue-200",
        icon: "text-blue-500",
        text: "text-blue-800",
        badge: "bg-blue-100 text-blue-800",
      };
  }
}

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === "error") {
    return (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  if (severity === "warning") {
    return (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function IssueCard({ violation }: { violation: DisplayViolation }) {
  const styles = getSeverityStyles(violation.severity);

  return (
    <div className={`p-4 rounded-lg border ${styles.bg} ${styles.border}`}>
      <div className="flex items-start">
        <div className={`flex-shrink-0 ${styles.icon}`}>
          <SeverityIcon severity={violation.severity} />
        </div>
        <div className="ml-3 flex-1">
          <div className="flex items-center justify-between">
            <h4 className={`text-sm font-medium ${styles.text}`}>
              {violation.message}
            </h4>
            <div className="flex items-center space-x-2">
              {violation.page !== null && violation.page > 0 && (
                <span className="text-xs text-gray-500">Page {violation.page}</span>
              )}
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles.badge}`}
              >
                {violation.severity}
              </span>
            </div>
          </div>
          <p className={`mt-1 text-sm ${styles.text} opacity-90`}>
            {violation.details}
          </p>
          {violation.suggestion && (
            <div className="mt-2 p-2 bg-white bg-opacity-50 rounded">
              <p className="text-sm text-gray-700">
                <span className="font-medium">Suggestion:</span>{" "}
                {violation.suggestion}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ComplianceReport({ report }: ComplianceReportProps) {
  const { passed, errorCount, warningCount, violations, pdfName, pagesChecked, universityName, timestamp } = report;

  const infoCount = violations.filter((v) => v.severity === "info").length;

  const groupedViolations = {
    errors: violations.filter((v) => v.severity === "error"),
    warnings: violations.filter((v) => v.severity === "warning"),
    info: violations.filter((v) => v.severity === "info"),
  };

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <div
        className={`p-6 rounded-xl ${
          passed
            ? "bg-gradient-to-r from-green-500 to-emerald-600"
            : "bg-gradient-to-r from-red-500 to-rose-600"
        } text-white`}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-3">
              {passed ? (
                <svg
                  className="h-10 w-10"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  className="h-10 w-10"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              <div>
                <h2 className="text-2xl font-bold">
                  {passed
                    ? "Compliance Check Passed!"
                    : "Issues Found"}
                </h2>
                <p className="text-white/80">
                  {passed
                    ? "Your thesis appears to meet formatting requirements."
                    : `${errorCount} error${errorCount !== 1 ? "s" : ""} need to be fixed before submission.`}
                </p>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">
              {errorCount + warningCount + infoCount}
            </div>
            <div className="text-sm text-white/80">Total issues</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-4">
          <div className="bg-white/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold">{errorCount}</div>
            <div className="text-sm text-white/80">Errors</div>
          </div>
          <div className="bg-white/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold">{warningCount}</div>
            <div className="text-sm text-white/80">Warnings</div>
          </div>
          <div className="bg-white/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold">{infoCount}</div>
            <div className="text-sm text-white/80">Info</div>
          </div>
        </div>
      </div>

      {/* Document Info */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-500 mb-2">
          Document Details
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">File:</span>
            <span className="ml-2 font-medium text-gray-900">{pdfName}</span>
          </div>
          <div>
            <span className="text-gray-500">Pages:</span>
            <span className="ml-2 font-medium text-gray-900">{pagesChecked}</span>
          </div>
          <div>
            <span className="text-gray-500">University:</span>
            <span className="ml-2 font-medium text-gray-900">
              {universityName}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Checked:</span>
            <span className="ml-2 font-medium text-gray-900">
              {new Date(timestamp).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Issues List */}
      {violations.length > 0 ? (
        <div className="space-y-6">
          {groupedViolations.errors.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-red-700 mb-3 flex items-center">
                <span className="bg-red-100 text-red-800 text-sm font-medium px-2 py-0.5 rounded mr-2">
                  {groupedViolations.errors.length}
                </span>
                Errors (Must Fix)
              </h3>
              <div className="space-y-3">
                {groupedViolations.errors.map((violation) => (
                  <IssueCard key={violation.id} violation={violation} />
                ))}
              </div>
            </div>
          )}

          {groupedViolations.warnings.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-yellow-700 mb-3 flex items-center">
                <span className="bg-yellow-100 text-yellow-800 text-sm font-medium px-2 py-0.5 rounded mr-2">
                  {groupedViolations.warnings.length}
                </span>
                Warnings (Review Recommended)
              </h3>
              <div className="space-y-3">
                {groupedViolations.warnings.map((violation) => (
                  <IssueCard key={violation.id} violation={violation} />
                ))}
              </div>
            </div>
          )}

          {groupedViolations.info.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-blue-700 mb-3 flex items-center">
                <span className="bg-blue-100 text-blue-800 text-sm font-medium px-2 py-0.5 rounded mr-2">
                  {groupedViolations.info.length}
                </span>
                Information (Manual Check)
              </h3>
              <div className="space-y-3">
                {groupedViolations.info.map((violation) => (
                  <IssueCard key={violation.id} violation={violation} />
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12 bg-green-50 rounded-lg">
          <svg
            className="mx-auto h-12 w-12 text-green-500"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <h3 className="mt-2 text-lg font-medium text-green-800">
            No issues detected!
          </h3>
          <p className="mt-1 text-sm text-green-600">
            Your document appears to comply with {universityName}&apos;s formatting
            requirements.
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t">
        <a
          href="/check"
          className="flex-1 inline-flex justify-center items-center px-6 py-3 border border-gray-300 rounded-lg text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          Check Another Document
        </a>
        <button
          onClick={() => window.print()}
          className="flex-1 inline-flex justify-center items-center px-6 py-3 border border-transparent rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors"
        >
          <svg
            className="h-5 w-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
            />
          </svg>
          Print Report
        </button>
      </div>
    </div>
  );
}
