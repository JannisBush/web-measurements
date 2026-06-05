# WebMeasurementReport v0.1

A static, dependency-free prototype for reporting active web measurements and exporting publication-ready tables to LaTeX.

## Quick Start

Open `index.html` in a browser, or serve the folder with any static file server:

```sh
python3 -m http.server 8000
```

The app stores drafts in browser `localStorage`. Use **Download JSON** to save a portable report file, or **Import JSON** to load a previous report.

## Features

### 📊 Two Table Modes

- **Compact Mode**: Streamlined view with one row per factor. Repeatable entries (like multiple browsers or data sources) are merged using smart formatting rules.
- **Full Mode**: Detailed view showing every individual field with its own status.

### 📑 Organized Export

LaTeX export includes:
- Group headers (Dataset, Crawler Basis, Environment, etc.)
- Clickable links using `\href{url}{text}` (requires hyperref package)
- Clean formatting with proper escaping
- Table* environment for two-column layouts

### 🔄 Version Control

When importing JSON files, the app checks version compatibility and warns if versions don't match, preventing data loss.

### ⚡ Smart Dependencies

Fields automatically become N/A when their dependencies aren't met. For example:
- Browser-related fields are disabled if crawler type is "Script-based"
- Internal page settings are disabled if page scope is "Landing page only"

A yellow notification shows why a field is automatically marked N/A.

### 💾 Auto-Save

All changes are automatically saved to browser localStorage. No manual save needed.

## Using the App

### Filling Out a Report

1. **Enter report title** in the metadata section
2. **Fill in factors** by group (Dataset, Crawler Basis, Environment, etc.)
3. **Set status** for each field:
   - **Reported**: You have data for this field
   - **Not applicable**: This field doesn't apply to your measurement
   - **Unknown**: You're unsure about this field
   - **Not reported**: You haven't filled this in yet
4. **Add notes** to provide references, justifications, or additional context

### Repeatable Factors

Some factors allow multiple entries (marked with "Add" button):

- **D-Site**: Add multiple data sources (Tranco, CrUX, etc.)
- **B-Instr**: Add multiple instrumentation tools
- **B-Brow**: Add multiple browsers or versions

Click **Add** to create new entries, **Remove** to delete them.

### Multi-Select Fields

For fields with multiple options (like "Pre-crawl removals" or "Collected raw data"):
- **macOS**: Hold **Cmd (⌘)** and click to select multiple
- **Windows/Linux**: Hold **Ctrl** and click to select multiple

### Viewing Results

Switch between **Compact** and **Full** table modes to see different levels of detail. Use the **All** / **Missing** filter to show only incomplete fields.

### Exporting

- **LaTeX**: Copy the generated LaTeX code for your paper
- **JSON**: Download a portable file to share or backup your report

## Editing the Registry

The factor registry lives in `registry.js` with three levels:

1. **Groups**: Major categories (D = Dataset, B = Crawler Basis, etc.)
2. **Factors**: Specific aspects (D-Site, B-Brow, etc.)
3. **Items**: Individual data fields

### Question Types

| Type | UI | Stored Value |
|------|-----|--------------|
| `select` | Dropdown | string |
| `multi` | Multi-select | array of strings |
| `text` | Single-line input | string |
| `textarea` | Multi-line input | string |
| `number` | Numeric input | string |
| `date` | Date picker | date string |
| `url` | URL input | string |

### Repeatable Factors

Enable multiple entries with `repeatable: true`:

```js
{
  id: "D-Site",
  label: "Website selection",
  repeatable: true,
  minEntries: 1,
  items: [...]
}
```

### Dependencies

Auto-disable fields based on other values:

```js
// Factor-level dependency
{
  id: "B-Brow",
  dependsOn: { itemId: "B-Type-Kind", values: ["Browser-based", "Hybrid"] },
  items: [...]
}

// Item-level dependency
{
  id: "D-Page-Limit",
  dependsOn: { itemId: "D-Page-Scope", values: ["Landing plus internal pages"] }
}
```

When dependencies aren't met, fields are automatically marked N/A with a yellow notification.

## Deploy on GitHub Pages

Since the app is plain HTML/CSS/JavaScript:

1. Push to GitHub
2. Enable GitHub Pages in repository settings
3. Select branch and root directory as source

## Technical Details

- **No dependencies**: Pure HTML, CSS, and JavaScript
- **No build step**: Edit and refresh
- **localStorage**: Automatic draft saving
- **Version checking**: Import validation
- **Smart escaping**: Proper LaTeX formatting with link support

## Current Scope

Version 0.1 targets active web measurements including:
- Browser-based and script-based crawls
- Controlled websites and applications
- Longitudinal measurements
- Multiple configurations within one design