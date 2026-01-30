"use client";

import { useState } from "react";
import type { SpecInfo } from "@/lib/types";

interface UniversitySelectProps {
  specs: SpecInfo[];
  selectedName: string | null;
  onSelect: (spec: SpecInfo) => void;
  disabled?: boolean;
}

export default function UniversitySelect({
  specs,
  selectedName,
  onSelect,
  disabled,
}: UniversitySelectProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredSpecs = specs.filter((spec) =>
    spec.university.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const selectedSpec = specs.find((s) => s.name === selectedName);

  return (
    <div className="w-full">
      <label
        htmlFor="university-search"
        className="block text-sm font-medium text-gray-700 mb-2"
      >
        Select Your University
      </label>
      <div className="relative">
        <input
          id="university-search"
          type="text"
          placeholder="Search universities..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          disabled={disabled}
          className={`
            w-full px-4 py-3 border border-gray-300 rounded-lg
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            ${disabled ? "opacity-50 cursor-not-allowed bg-gray-100" : "bg-white"}
          `}
        />
        <svg
          className="absolute right-3 top-3.5 h-5 w-5 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      <div className="mt-3 max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
        {filteredSpecs.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500">
            <p>No universities found</p>
            <p className="text-sm mt-1">
              Try a different search term
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {filteredSpecs.map((spec) => (
              <li key={spec.name}>
                <button
                  type="button"
                  onClick={() => onSelect(spec)}
                  disabled={disabled}
                  className={`
                    w-full px-4 py-3 text-left transition-colors
                    ${disabled ? "cursor-not-allowed" : "hover:bg-gray-50"}
                    ${selectedName === spec.name ? "bg-blue-50 border-l-4 border-blue-500" : ""}
                  `}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{spec.university}</p>
                      <p className="text-sm text-gray-500">
                        {spec.description} ({spec.rule_count} rules)
                      </p>
                    </div>
                    {selectedName === spec.name && (
                      <svg
                        className="h-5 w-5 text-blue-500"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selectedSpec && (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-start">
            <svg
              className="h-5 w-5 text-blue-500 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3">
              <h4 className="text-sm font-medium text-blue-800">
                {selectedSpec.university}
              </h4>
              <p className="mt-1 text-sm text-blue-700">
                {selectedSpec.description}
              </p>
              <p className="mt-1 text-sm text-blue-600">
                Spec version: {selectedSpec.version} | {selectedSpec.rule_count} formatting rules
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
