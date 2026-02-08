# Prompt 15: View Deep-Link Evidence Focus - Smoke Test

## Overview
Manual smoke test checklist for verifying deep-link evidence focus functionality from OCR Extractions panel.

## Prerequisites
1. Case with documents uploaded and OCR run
2. OCR Extractions available (run Autofill to generate candidates)
3. At least one extraction candidate with evidence details

## Test Steps

### Step 1: Access OCR Extractions Panel
1. Navigate to a case detail page: `/cases/<CASE_ID>`
2. Click on "OCR Extractions" tab
3. Open an extraction candidate drawer by clicking "View evidence" on any extraction item
4. Verify the drawer shows:
   - Field key
   - Proposed value
   - Page number
   - **"View in document" button** (NEW - should appear next to page number)

### Step 2: Click "View in document" Button
1. Click the "View in document" button in the evidence drawer
2. **Expected**: Page navigates to Documents tab with URL:
   ```
   /cases/<CASE_ID>?tab=documents&focusDocId=<DOC_ID>&focusPage=<PAGE_NUM>&focusCandidateId=<CANDIDATE_ID>
   ```

### Step 3: Verify Deep-Link State
1. **Expected URL Params**:
   - `tab=documents` ✓
   - `focusDocId=<document_id>` ✓
   - `focusPage=<page_number>` ✓
   - `focusCandidateId=<candidate_id>` ✓ (optional)

2. **Expected UI State**:
   - Documents tab is active ✓
   - Correct document is selected (highlighted in document list) ✓
   - **Callout banner appears**: "Evidence focus: Page X" (where X is the focused page number) ✓
   - Focused page button is highlighted:
     - Cyan background (`bg-cyan-500`)
     - White text
     - Cyan border and ring (`ring-2 ring-cyan-400`)
   - Focused page button scrolls into view (smooth scroll, centered in viewport) ✓

### Step 4: Test Direct URL Access
1. Construct URL manually:
   ```
   http://localhost:3000/cases/<CASE_ID>?tab=documents&focusDocId=<DOC_ID>&focusPage=4
   ```
   Replace:
   - `<CASE_ID>`: Actual case ID
   - `<DOC_ID>`: Actual document ID (from document list)
   - `4`: Page number (use any valid page number for the document)

2. Navigate to this URL directly (or copy/paste)
3. **Expected**: Same behavior as Step 3:
   - Documents tab active ✓
   - Correct document selected ✓
   - Callout shows "Evidence focus: Page 4" ✓
   - Page 4 button highlighted and scrolled into view ✓

### Step 5: Browser Console Check
1. Open browser DevTools (F12)
2. Check Console tab
3. **Expected**: No runtime errors ✓
4. **Expected**: No warnings about undefined DOM elements ✓

### Step 6: Edge Cases
1. **Invalid page number**:
   - Use URL: `?focusDocId=<DOC_ID>&focusPage=999` (page doesn't exist)
   - **Expected**: Callout doesn't appear, no error in console ✓

2. **Invalid document ID**:
   - Use URL: `?focusDocId=invalid-id&focusPage=1`
   - **Expected**: Document not selected, no error in console ✓

3. **Missing params**:
   - Use URL: `?tab=documents` (no focus params)
   - **Expected**: Normal documents tab view, no callout ✓

## Test Template - Copy/Paste Ready

### Example URL Format:
```
http://localhost:3000/cases/<CASE_ID>?tab=documents&focusDocId=<DOC_ID>&focusPage=4&focusCandidateId=<CANDIDATE_ID>
```

### Quick Test Command (replace placeholders):
```bash
# 1. Get a case ID from your database or UI
CASE_ID="your-case-id"

# 2. Get a document ID from the case
DOC_ID="your-doc-id"

# 3. Use page 4 (or any valid page)
PAGE_NUM=4

# 4. Open in browser
open "http://localhost:3000/cases/${CASE_ID}?tab=documents&focusDocId=${DOC_ID}&focusPage=${PAGE_NUM}"
```

## Expected UI Outcomes

### Visual Indicators:
1. **Callout Banner** (appears at top of document detail panel):
   ```
   ┌─────────────────────────────────────┐
   │ Evidence focus: Page 4              │
   └─────────────────────────────────────┘
   ```
   - Cyan background (`bg-cyan-500/20`)
   - Cyan border (`border-cyan-500`)
   - Cyan text (`text-cyan-400`)

2. **Highlighted Page Button**:
   - Normal page button: Gray background (`bg-slate-700`)
   - Focused page button: Cyan background (`bg-cyan-500`), white text, ring highlight

3. **Scroll Behavior**:
   - Smooth scroll animation
   - Focused button centered in viewport
   - Only triggers when focus params are present in URL

## Notes

- **No PDF snippet highlight is expected** (as per requirements)
- URL params are shareable/copy-pasteable
- Backward compatibility: Old params (`docId`, `page`) still work
- New params (`focusDocId`, `focusPage`, `focusCandidateId`) are preferred for deep linking

## Troubleshooting

1. **Callout doesn't appear**:
   - Check that `focusDocId` and `focusPage` are in URL
   - Verify document ID exists in documents list
   - Check browser console for errors

2. **Page button not scrolling**:
   - Verify `focusPage` is a valid page number for the document
   - Check that document is selected before scrolling
   - Wait for page render (scroll happens after 100ms delay)

3. **Wrong document selected**:
   - Verify `focusDocId` matches a document in the case
   - Check that documents have loaded (wait for initial load)

## Success Criteria

✅ "View in document" button appears in evidence drawer  
✅ Clicking button navigates with correct URL params  
✅ Direct URL access works correctly  
✅ Callout banner appears when focus params are present  
✅ Focused page button is highlighted  
✅ Focused page button scrolls into view  
✅ No console errors  
✅ Backward compatibility maintained (old params still work)
