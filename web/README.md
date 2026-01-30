# ThesisCheck

**Never get your thesis rejected for formatting again.**

ThesisCheck is a web-based tool that validates thesis/dissertation PDF formatting against university-specific requirements in real-time.

## Features

- **PDF Upload**: Drag-and-drop or click to upload your thesis PDF
- **University Selection**: Choose from 8 supported universities (and growing)
- **Instant Compliance Report**: Get detailed feedback on formatting issues
- **Issue Categorization**: Errors (must fix), Warnings (review), and Info (manual check)
- **Actionable Suggestions**: Each issue includes specific fix recommendations

## Supported Universities

- Rice University
- University of North Carolina at Chapel Hill
- Cornell University
- University of Notre Dame
- Massachusetts Institute of Technology
- Stanford University
- University of California, Berkeley
- University of Illinois Urbana-Champaign

## What We Check

- **Margins**: Left, right, top, and bottom margin compliance
- **Page Size**: US Letter (8.5" x 11") validation
- **Page Orientation**: Portrait vs landscape detection
- **Page Numbers**: Position and style requirements
- **Font Requirements**: Size ranges (coming soon)
- **Line Spacing**: Double spacing verification (coming soon)

## Getting Started

### Prerequisites

- Node.js 18.x or later
- npm

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/thesis-check.git
cd thesis-check

# Install dependencies
npm install

# Run the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS
- **PDF Processing**: pdf-lib
- **Language**: TypeScript

## Project Structure

```
thesis-check/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Landing page
│   │   ├── check/page.tsx        # Upload & check page
│   │   ├── api/analyze/route.ts  # PDF analysis API
│   │   ├── layout.tsx            # Root layout
│   │   └── globals.css           # Global styles
│   ├── components/
│   │   ├── FileUpload.tsx        # PDF upload component
│   │   ├── UniversitySelect.tsx  # University selector
│   │   └── ComplianceReport.tsx  # Results display
│   └── lib/
│       ├── universities.json     # University rules database
│       ├── types.ts              # TypeScript types
│       ├── pdf-analyzer.ts       # PDF parsing logic
│       └── compliance-checker.ts # Rule validation
```

## Adding a New University

1. Open `src/lib/universities.json`
2. Add a new entry following the existing schema:

```json
{
  "id": "your_university",
  "name": "Your University Name",
  "guide_url": "https://...",
  "rules": {
    "margins": { "left": 1.5, "right": 1.0, "top": 1.0, "bottom": 1.0, "tolerance": 0.05 },
    "fonts": { "min_size": 10, "max_size": 12, "allowed_families": [...] },
    "spacing": { "line_spacing": "double", "paragraph_spacing": "consistent" },
    "page_numbers": { "position": "bottom-center", ... },
    "headings": { "chapter_new_page": true, "min_lines_after_heading": 2 },
    "widows_orphans": { "max_orphan_lines": 1, "max_widow_lines": 1 }
  }
}
```

## Future Enhancements

- [ ] Font size detection from PDF
- [ ] Line spacing measurement
- [ ] Widow/orphan line detection
- [ ] Heading placement validation
- [ ] Table of Contents format checking
- [ ] User accounts and history
- [ ] Institutional licensing

## Deploy on Vercel

The easiest way to deploy ThesisCheck is on [Vercel](https://vercel.com):

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/thesis-check)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Disclaimer

ThesisCheck provides automated formatting checks as a helpful tool. Always verify compliance with your graduate school's official guidelines before final submission.
