-- AppleScript to extract text from PDFs using Preview
-- Save this file as extract_with_preview.applescript

on run argv
	-- Check if parameters were provided
	if (count of argv) < 2 then
		log "Usage: osascript extract_with_preview.applescript input_pdf output_txt"
		return "ERROR: Missing parameters"
	end if
	
	set pdf_path to item 1 of argv
	set output_path to item 2 of argv
	
	-- Extract text from PDF
	set extracted_text to extract_text_from_pdf(pdf_path)
	
	-- Write to output file using do shell script instead of file operations
	if extracted_text is not "" then
		try
			-- Use echo command and redirect to the file
			do shell script "echo " & quoted form of extracted_text & " > " & quoted form of output_path
			return "SUCCESS: Text extracted to " & output_path
		on error errMsg
			return "ERROR writing file: " & errMsg
		end try
	else
		return "ERROR: No text extracted from PDF"
	end if
end run

on extract_text_from_pdf(pdf_path)
	set extracted_text to ""
	set wasRunning to false
	
	-- Check if Preview is already running
	tell application "System Events"
		if exists process "Preview" then
			set wasRunning to true
		end if
	end tell
	
	-- Extract text using Preview
	try
		tell application "Preview"
			-- Open the PDF
			open pdf_path
			
			-- Get document info
			set doc_ref to document 1
			set doc_name to name of doc_ref
			
			-- Wait for document to load
			delay 2
			
			tell application "System Events"
				tell process "Preview"
					-- Make sure it's frontmost
					set frontmost to true
					delay 0.5
					
					-- Select all text
					keystroke "a" using {command down}
					delay 1
					
					-- Copy to clipboard
					keystroke "c" using {command down}
					delay 1
				end tell
			end tell
			
			-- Get text from clipboard
			set extracted_text to the clipboard
			
			-- Close document
			close doc_ref
			
			-- Quit Preview if it wasn't running before
			if not wasRunning then
				quit
			end if
		end tell
		
		return extracted_text
	on error errMsg
		-- Clean up in case of error
		try
			tell application "Preview"
				if not wasRunning then
					quit
				end if
			end tell
		end try
		
		return ""
	end try
end extract_text_from_pdf
