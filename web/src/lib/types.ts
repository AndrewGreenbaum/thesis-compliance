// Types adapted for Python backend API

export type IssueSeverity = "error" | "warning" | "info";

// Python API violation format
export interface Violation {
  rule_id: string;
  rule_type: string;
  severity: "ERROR" | "WARNING" | "INFO";
  message: string;
  page: number | null;
  expected: number | string | null;
  found: number | string | null;
  suggestion: string | null;
}

// Python API response from /check endpoint
export interface CheckResponse {
  pdf_name: string;
  spec_name: string;
  pages_checked: number;
  rules_checked: number;
  passed: boolean;
  error_count: number;
  warning_count: number;
  violations: Violation[];
}

// Python API response from /specs endpoint
export interface SpecInfo {
  name: string;
  university: string;
  description: string;
  version: string;
  rule_count: number;
}

// Frontend-friendly format for display (transformed from CheckResponse)
export interface ComplianceReport {
  pdfName: string;
  specName: string;
  universityName: string;
  pagesChecked: number;
  passed: boolean;
  errorCount: number;
  warningCount: number;
  violations: DisplayViolation[];
  timestamp: string;
}

// Frontend-friendly violation format for display
export interface DisplayViolation {
  id: string;
  ruleId: string;
  ruleType: string;
  severity: IssueSeverity;
  message: string;
  page: number | null;
  details: string;
  suggestion: string | null;
}

// Transform Python API response to frontend format
export function transformCheckResponse(
  response: CheckResponse,
  universityName: string
): ComplianceReport {
  return {
    pdfName: response.pdf_name,
    specName: response.spec_name,
    universityName,
    pagesChecked: response.pages_checked,
    passed: response.passed,
    errorCount: response.error_count,
    warningCount: response.warning_count,
    violations: response.violations.map((v, index) => ({
      id: `${v.rule_id}-${index}`,
      ruleId: v.rule_id,
      ruleType: v.rule_type,
      severity: v.severity.toLowerCase() as IssueSeverity,
      message: v.message,
      page: v.page,
      details: formatViolationDetails(v),
      suggestion: v.suggestion,
    })),
    timestamp: new Date().toISOString(),
  };
}

function formatViolationDetails(violation: Violation): string {
  const parts: string[] = [];

  if (violation.expected !== null && violation.found !== null) {
    parts.push(`Expected: ${violation.expected}, Found: ${violation.found}`);
  } else if (violation.expected !== null) {
    parts.push(`Expected: ${violation.expected}`);
  } else if (violation.found !== null) {
    parts.push(`Found: ${violation.found}`);
  }

  if (parts.length === 0) {
    return violation.message;
  }

  return parts.join(". ");
}
