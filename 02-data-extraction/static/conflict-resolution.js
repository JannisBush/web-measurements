/**
 * Conflict Resolution JavaScript Functionality
 * Handles question detail expansion/collapse, coder response selection,
 * final outcome editing, and progress tracking
 */
function findObjectByName(data, targetName) {
  if (Array.isArray(data)) {
    for (const item of data) {
      const result = findObjectByName(item, targetName);
      if (result) return result;
    }
  } else if (data && typeof data === "object") {
    if (data.name === targetName) return data;

    for (const key of Object.keys(data)) {
      const result = findObjectByName(data[key], targetName);
      if (result) return result;
    }
  }
  return null;
}

class ConflictResolutionManager {
    constructor(paperId, availableCoders, mode = 'final', coderName = null, schema = null) {
        this.paperId = paperId;
        this.availableCoders = availableCoders;
        this.mode = mode; // 'initial' or 'final'
        this.coderName = coderName; // For initial resolution
        this.schema = schema; // Survey schema for button availability
        this.conflictData = null;
        this.questionMetadataCache = {};
        this.showAllQuestions = false; // Toggle state
        this.hideResolved = false; // Toggle state for hiding resolved conflicts
        
        // Track hide timeouts for resolved questions
        this.hideTimeouts = new Map(); // Map of questionId -> timeout handle
        
        // Initialize the interface
        this.init();
    }
    
    async init() {
        await this.loadConflictData();
    }
    
    /**
     * Toggle between showing all questions vs conflicts only
     */
    toggleView() {
        this.showAllQuestions = !this.showAllQuestions;
        
        const toggleBtn = document.getElementById('toggle-view-btn');
        const hideResolvedBtn = document.getElementById('hide-resolved-btn');
        const viewStatus = document.getElementById('view-status');
        
        if (!toggleBtn) {
            return;
        }
        
        if (this.showAllQuestions) {
            toggleBtn.textContent = 'Show Conflicts Only';
            hideResolvedBtn.style.display = 'none'; // Hide the "Hide Resolved" button in "Show All" mode
            viewStatus.textContent = 'Currently showing: All questions';
        } else {
            toggleBtn.textContent = 'Show All Questions';
            hideResolvedBtn.style.display = 'inline-block'; // Show the "Hide Resolved" button in "Conflicts Only" mode
        }
        this.updateViewStatus();
        this.renderQuestions();
        this.updateProgress();
    }
    
    /**
     * Toggle hiding resolved conflicts (only available in conflicts-only mode)
     */
    toggleHideResolved() {
        this.hideResolved = !this.hideResolved;
        this.updateViewStatus();
        this.renderQuestions();
        this.updateProgress();
    }
    
    /**
     * Update the view status text based on current settings
     */
    updateViewStatus() {
        const viewStatus = document.getElementById('view-status');
        const hideResolvedBtn = document.getElementById('hide-resolved-btn');
        
        // These elements don't exist in initial resolution mode
        if (!viewStatus) {
            return;
        }
        
        if (this.showAllQuestions) {
            viewStatus.textContent = 'Currently showing: All questions';
            if (hideResolvedBtn) {
                hideResolvedBtn.style.display = 'none';
            }
        } else {
            if (hideResolvedBtn) {
                hideResolvedBtn.style.display = 'inline-block';
            }
            
            if (this.hideResolved) {
                viewStatus.textContent = 'Currently showing: Active conflicts only (resolved hidden)';
                if (hideResolvedBtn) {
                    hideResolvedBtn.textContent = 'Show Resolved';
                }
            } else {
                viewStatus.textContent = 'Currently showing: All conflicts';
                if (hideResolvedBtn) {
                    hideResolvedBtn.textContent = 'Hide Resolved';
                }
            }
        }
    }
    
    /**
     * Task 4.1: Question Detail Expansion/Collapse Functionality
     * Toggle question text and options visibility
     * Load question metadata via API calls
     */
    async toggleQuestionDetails(questionId) {
        const detailsDiv = document.getElementById(`details-${questionId}`);
        const icon = document.getElementById(`icon-${questionId}`);
        
        if (!detailsDiv || !icon) {
            return; // Safety check
        }
        
        if (detailsDiv.classList.contains('expanded')) {
            // Collapse the details
            detailsDiv.classList.remove('expanded');
            icon.textContent = '▶';
        } else {
            // Expand the details
            detailsDiv.classList.add('expanded');
            icon.textContent = '▼';
            
            // Load question metadata if not cached
            if (!this.questionMetadataCache[questionId]) {
                await this.loadQuestionMetadata(questionId);
            }
            
            this.renderQuestionDetails(questionId);
        }
    }
    
    async loadQuestionMetadata(questionId) {
        let fetchId = questionId;
        if (questionId.endsWith('-Comment')) {
            fetchId = questionId.replace('-Comment', '');
        }
        try {
            const response = await fetch(`/api/question/${fetchId}`);
            if (response.ok) {
                this.questionMetadataCache[questionId] = await response.json();
            } else {
                this.questionMetadataCache[questionId] = { error: 'Failed to load metadata' };
            }
        } catch (error) {
            console.error(`Error loading metadata for ${questionId}:`, error);
            this.questionMetadataCache[questionId] = { error: error.message };
        }
    }
    
    renderQuestionDetails(questionId) {
        const detailsDiv = document.getElementById(`details-${questionId}`);
        const metadata = this.questionMetadataCache[questionId];
        
        if (!metadata || metadata.error) {
            detailsDiv.innerHTML = `<div class="error">Error loading question details</div>`;
            return;
        }
        

        let html = `<div class="question-text">${metadata.title || metadata.question_id}</div>`;
        // Always check for comments for this question
        this.loadAndDisplayCommentsInDetails(questionId, html, metadata);
    }
    
    async loadAndDisplayCommentsInDetails(questionId, baseHtml, metadata) {
        const detailsDiv = document.getElementById(`details-${questionId}`);
        
        try {
            // Check if there are comments for this question
            const commentQuestionId = `${questionId}-Comment`;
            const coderNames = Object.keys(this.conflictData.coder_data);
            
            let hasComments = false;
            let commentData = {};
            
            // Check if any coder has comments for this question
            for (const coderName of coderNames) {
                const commentValue = this.conflictData.coder_data[coderName].responses[commentQuestionId];
                if (commentValue && commentValue.trim() !== '') {
                    hasComments = true;
                    commentData[coderName] = { comment: commentValue };
                }
            }
            
            let html = baseHtml;

            if (!questionId.endsWith('-Comment')) {
            
                // If there are comments, display them
                if (hasComments) {
                    html += `<div class="comment-section">`;
                    html += `<div class="comment-header">💬 Comments for this question:</div>`;
                    html += `<div class="comment-comparison">`;
                    
                    for (const coderName of coderNames) {
                        const comment = commentData[coderName]?.comment || 'No comment';
                        
                        html += `
                            <div class="comment-item">
                                <div class="comment-coder">${coderName}:</div>
                                <div class="comment-text">${this.escapeHtml(comment)}</div>
                            </div>
                        `;
                    }
                    
                    html += `</div></div>`; // Close comment-comparison and comment-section
                }
                
                // Show options if available
                if (metadata.options && metadata.options.length > 0) {
                    html += `
                        <div class="question-options">
                            <div class="question-options-title">Available Options (click to select):</div>
                    `;
                    
                    for (const option of metadata.options) {
                        const optionValue = option.value || option;
                        const optionText = option.text || option;
                        html += `
                            <div class="option-item" data-value="${this.escapeHtml(optionValue)}" onclick="conflictManager.selectOption('${questionId}', '${this.escapeHtml(optionValue)}')">
                                ${this.escapeHtml(optionText)} (${this.escapeHtml(optionValue)})
                            </div>
                        `;
                    }
                    
                    html += `</div>`;
                }
                
                // Show conditional logic if present
                if (metadata.visible_if || metadata.enable_if) {
                    html += `<div class="conditional-logic-section">`;
                    
                    if (metadata.visible_if) {
                        const formattedCondition = metadata.visible_if_formatted || metadata.visible_if;
                        html += `
                            <div class="conditional-info visibility">
                                <div class="conditional-header">
                                    <span class="conditional-icon">👁</span>
                                    <strong>Visibility Condition:</strong>
                                </div>
                                <div class="conditional-text">This question is visible when: ${formattedCondition}</div>
                                <div class="conditional-raw">Raw condition: <code>${metadata.visible_if}</code></div>
                            </div>
                        `;
                    }
                    
                    if (metadata.enable_if) {
                        const formattedCondition = metadata.enable_if_formatted || metadata.enable_if;
                        html += `
                            <div class="conditional-info enabled">
                                <div class="conditional-header">
                                    <span class="conditional-icon">⚙</span>
                                    <strong>Enable Condition:</strong>
                                </div>
                                <div class="conditional-text">This question is enabled when: ${formattedCondition}</div>
                                <div class="conditional-raw">Raw condition: <code>${metadata.enable_if}</code></div>
                            </div>
                        `;
                    }
                    
                    // Show dependencies if present
                    if (metadata.dependencies && metadata.dependencies.length > 0) {
                        html += `
                            <div class="dependencies-info">
                                <div class="conditional-header">
                                    <span class="conditional-icon">🔗</span>
                                    <strong>Dependencies:</strong>
                                </div>
                                <div class="conditional-text">This question depends on: ${metadata.dependencies.join(', ')}</div>
                            </div>
                        `;
                    }
                    
                    html += `</div>`;
                }
            };
            
            detailsDiv.innerHTML = html;
            
            // Update option styling based on current final value
            this.updateOptionStylingFromFinalValue(questionId);
            
        } catch (error) {
            console.error('Error loading comments in details:', error);
            // Fallback to basic display without comments
            let html = baseHtml;
            
            // Show options if available
            if (metadata.options && metadata.options.length > 0) {
                html += `
                    <div class="question-options">
                        <div class="question-options-title">Available Options (click to select):</div>
                `;
                
                for (const option of metadata.options) {
                    const optionValue = option.value || option;
                    const optionText = option.text || option;
                    html += `
                        <div class="option-item" data-value="${this.escapeHtml(optionValue)}" onclick="conflictManager.selectOption('${questionId}', '${this.escapeHtml(optionValue)}')">
                            ${this.escapeHtml(optionText)}
                        </div>
                    `;
                }
                
                html += `</div>`;
            }
            
            detailsDiv.innerHTML = html + `<div class="error">Could not load comment data</div>`;
        }
    }

    async loadAndDisplayComments(questionId, baseHtml) {
        const detailsDiv = document.getElementById(`details-${questionId}`);
        
        try {
            const response = await fetch(`/api/conflicts/${this.paperId}/question/${questionId}/with-comments`);
            if (response.ok) {
                const commentData = await response.json();
                
                let html = baseHtml;
                
                // Display comments from each coder (no conflict indicator)
                const coderNames = Object.keys(commentData.coder_data);
                html += `<div class="comment-comparison">`;
                
                for (const coderName of coderNames) {
                    const coderData = commentData.coder_data[coderName];
                    const comment = coderData.comment || '<em>No comment</em>';
                    
                    html += `
                        <div class="comment-item">
                            <div class="comment-coder">${coderName}:</div>
                            <div class="comment-text">${this.escapeHtml(comment)}</div>
                        </div>
                    `;
                }
                
                html += `</div></div>`; // Close comment-comparison and comment-section
                
                // Add the rest of the question details
                const metadata = this.questionMetadataCache[questionId];
                
                // Show options if available
                if (metadata.options && metadata.options.length > 0) {
                    html += `
                        <div class="question-options">
                            <div class="question-options-title">Available Options (click to select):</div>
                    `;
                    
                    for (const option of metadata.options) {
                        const optionValue = option.value || option;
                        const optionText = option.text || option;
                        html += `
                            <div class="option-item" data-value="${this.escapeHtml(optionValue)}" onclick="conflictManager.selectOption('${questionId}', '${this.escapeHtml(optionValue)}')">
                                ${this.escapeHtml(optionText)}
                            </div>
                        `;
                    }
                    
                    html += `</div>`;
                }
                
                detailsDiv.innerHTML = html;
                
                // Update option styling based on current final value
                this.updateOptionStylingFromFinalValue(questionId);
                
            } else {
                // Fallback to basic display without comments
                detailsDiv.innerHTML = baseHtml + `<div class="error">Could not load comment data</div>`;
            }
            
        } catch (error) {
            console.error('Error loading comments:', error);
            detailsDiv.innerHTML = baseHtml + `<div class="error">Error loading comment data</div>`;
        }
    }
    
    /**
     * Task 4.2: Coder Response Selection Functionality
     * Click handlers for coder 1 and coder 2 responses
     * Click handlers for available question options
     * Update final outcome field with selected values
     */
    selectCoderResponse(questionId, coderName) {
        const value = this.conflictData.coder_data[coderName].responses[questionId];
        const input = document.querySelector(`#final-${questionId} textarea`);
        
        // Handle undefined/null values properly
        let processedValue = value;
        if (value === undefined || value === null) {
            processedValue = '';  // Convert to empty string for consistency
        }
        
        // Add coder name prefix for comment fields
        let q_meta = findObjectByName(this.conflictData.schema, questionId);
        if (((q_meta["type"] == "text" || q_meta["type"] == "comment") && q_meta.inputType != 'number') || (questionId.endsWith('-Comment') && processedValue && String(processedValue).trim() !== '')) {
            processedValue = `(${coderName}:) ${processedValue}`;
        }
        
        // Store the actual value in data attribute
        input.setAttribute('data-actual-value', JSON.stringify(processedValue));
        
        // Format the value properly for display in input field
        const formattedValue = this.formatValueForInput(processedValue);
        input.value = formattedValue;
        
        // Use the actual value (not formatted) for the update
        this.updateFinalOutcome(questionId, processedValue);
    }
    
    /**
     * Get available buttons for initial resolution
     */
    getAvailableButtons(questionId) {
        if (this.mode !== 'initial') {
            return []; // Not applicable for final resolution
        }
        
        // Comments cannot be resolved in initial resolution
        if (questionId.endsWith('-Comment')) {
            return [];
        }
        
        // Get coder names from conflict data
        const coderNames = Object.keys(this.conflictData.coder_data || {});
        
        if (coderNames.length < 2) {
            console.error('Not enough coder names found in conflict data');
            return ['A', 'B', 'Discuss']; // Fallback to A/B if coder names not available
        }
        
        // Use actual coder names instead of A and B
        const buttons = [coderNames[0], coderNames[1], 'Discuss'];
        
        // Check if Union button should be available
        let q_meta = findObjectByName(this.schema, questionId);
        
        if (!q_meta) {
            return buttons; // Default buttons if metadata not found
        }
        
        // Union available for:
        // 1. Checkbox (multi-select)
        // 2. Text fields that are not numbers
        if (q_meta["type"] === 'checkbox') {
            buttons.splice(2, 0, 'Union'); // Add Union before Discuss
        } else if ((q_meta["type"] === 'text' && q_meta.inputType !== 'number') || q_meta["type"] == 'comment') {
            buttons.splice(2, 0, 'Union'); // Add Union before Discuss
        }
        
        return buttons;
    }
    
    /**
     * Render buttons for initial resolution
     */
    renderInitialResolutionButtons(questionId, currentDecision = null, hasConflict = true) {
        // If not a conflict, show "No resolution needed"
        if (!hasConflict) {
            return '<div class="initial-resolution-disabled">✓ No resolution needed (coders agree)</div>';
        }
        
        const buttons = this.getAvailableButtons(questionId);
        
        if (buttons.length === 0) {
            return '<div class="initial-resolution-disabled">No resolution needed</div>';
        }
        
        let html = '<div class="initial-resolution-buttons">';
        
        for (const button of buttons) {
            const isSelected = currentDecision === button;
            const selectedClass = isSelected ? 'selected' : '';
            html += `
                <button 
                    class="resolution-btn resolution-btn-${button.toLowerCase()} ${selectedClass}"
                    onclick="conflictManager.selectInitialResolution('${questionId}', '${button}')"
                    data-decision="${button}">
                    ${button}
                </button>
            `;
        }
        
        html += '</div>';
        return html;
    }
    
    /**
     * Handle initial resolution button click
     */
    async selectInitialResolution(questionId, decision) {
        if (this.mode !== 'initial') {
            console.error('Initial resolution only available in initial mode');
            return;
        }
        
        try {
            const response = await fetch(`/api/initial-resolution/${this.paperId}/${questionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    decision: decision,
                    coder_name: this.coderName
                })
            });
            
            if (response.ok) {
                // Update UI to show selection
                const buttonsContainer = document.querySelector(`#final-${questionId} .initial-resolution-buttons`);
                if (buttonsContainer) {
                    // Remove selected class from all buttons
                    buttonsContainer.querySelectorAll('.resolution-btn').forEach(btn => {
                        btn.classList.remove('selected');
                    });
                    
                    // Add selected class to clicked button
                    const clickedBtn = buttonsContainer.querySelector(`[data-decision="${decision}"]`);
                    if (clickedBtn) {
                        clickedBtn.classList.add('selected');
                    }
                }
                
                // Update local data
                if (!this.conflictData.initial_resolutions) {
                    this.conflictData.initial_resolutions = {};
                }
                this.conflictData.initial_resolutions[questionId] = decision;
                
                // Update row styling to show as resolved
                const questionRow = document.getElementById(`question-${questionId}`);
                if (questionRow) {
                    // Remove unresolved styling
                    questionRow.classList.remove('conflict', 'unresolved-highlight');
                    questionRow.classList.add('resolved');
                    
                    // Remove any existing indicators first
                    const existingIndicator = questionRow.querySelector('.resolution-indicator');
                    if (existingIndicator) {
                        existingIndicator.remove();
                    }
                    
                    // Add resolved indicator
                    this.addResolvedIndicatorForInitial(questionRow, questionId, decision);
                    
                    // If hideResolved is enabled, hide the row after a short delay
                    if (this.hideResolved && !this.showAllQuestions) {
                        setTimeout(() => {
                            if (this.hideResolved && !this.showAllQuestions && questionRow) {
                                questionRow.style.display = 'none';
                                
                                // After hiding, auto-expand the next unresolved question
                                setTimeout(() => {
                                    const firstUnresolved = Array.from(document.getElementById('questions-list').children)
                                        .find(el => el.tagName === 'DIV' && 
                                                   el.style.display !== 'none' &&
                                                   !el.classList.contains('resolved') && 
                                                   el.classList.contains('conflict'));
                                    if (firstUnresolved) {
                                        const questionId = firstUnresolved.id.slice(9); // Remove 'question-' prefix
                                        this.toggleQuestionDetails(questionId);
                                    }
                                }, 100);
                            }
                        }, 500);
                    }
                }
                
                // Update progress
                this.updateProgress();
                
                // Show save indicator
                const saveIndicator = document.getElementById(`save-${questionId}`);
                if (saveIndicator) {
                    saveIndicator.classList.add('show');
                    saveIndicator.textContent = '✓ Saved';
                    saveIndicator.style.color = '#28a745';
                    
                    setTimeout(() => {
                        saveIndicator.classList.remove('show');
                    }, 2000);
                }
            } else {
                const errorData = await response.json();
                console.error('Error saving initial resolution:', errorData);
                alert('Error saving decision: ' + (errorData.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Network error saving initial resolution:', error);
            alert('Network error. Please check your connection and try again.');
        }
    }
    
    /**
     * Add resolved indicator for initial resolution
     */
    addResolvedIndicatorForInitial(questionRow, questionId, decision) {
        // Remove any existing indicator
        const existingIndicator = questionRow.querySelector('.resolution-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Add new indicator
        const indicator = document.createElement('div');
        indicator.className = 'resolution-indicator resolved-indicator';
        indicator.innerHTML = '✓';
        indicator.title = `Decision: ${decision}`;
        
        const questionHeader = questionRow.querySelector('.question-header');
        if (questionHeader) {
            questionHeader.appendChild(indicator);
        }
    }
    
    selectOption(questionId, optionValue) {
        const input = document.querySelector(`#final-${questionId} textarea`);
        
        // Check if this question supports multiple selections by looking at metadata
        const metadata = this.questionMetadataCache[questionId];
        const isMultiSelect = metadata && metadata.type === 'checkbox';
        
        if (isMultiSelect) {
            // Handle multiple selection for checkbox questions
            let currentValues = [];
            
            // Get actual values from data attribute (not display values)
            try {
                const actualValue = JSON.parse(input.getAttribute('data-actual-value') || '[]');
                if (Array.isArray(actualValue)) {
                    currentValues = actualValue;
                } else if (actualValue) {
                    currentValues = [actualValue];
                }
            } catch (e) {
                // Fallback to parsing display value if data attribute is not available
                const currentValue = input.value.trim();
                if (currentValue) {
                    currentValues = currentValue.split(',').map(v => v.trim()).filter(v => v);
                }
            }
            
            // Toggle the option
            const optionIndex = currentValues.indexOf(optionValue);
            if (optionIndex > -1) {
                // Remove if already selected
                currentValues.splice(optionIndex, 1);
            } else {
                // Add if not selected
                currentValues.push(optionValue);
            }
            
            // Store actual value as array in data attribute
            input.setAttribute('data-actual-value', JSON.stringify(currentValues));
            
            // Update display value (formatted)
            input.value = currentValues.join(', ');
            
            // Send array to backend (not string)
            this.updateFinalOutcome(questionId, currentValues);
            
            // Update visual styling of options
            this.updateOptionStyling(questionId, currentValues);
        } else {
            // Handle single selection for other question types
            input.setAttribute('data-actual-value', JSON.stringify(optionValue));
            input.value = optionValue;
            this.updateFinalOutcome(questionId, optionValue);
            
            // Update visual styling of options
            this.updateOptionStyling(questionId, [optionValue]);
        }
    }
    
    /**
     * Update visual styling of option items to show which are selected
     */
    updateOptionStyling(questionId, selectedValues) {
        const detailsDiv = document.getElementById(`details-${questionId}`);
        if (!detailsDiv) return;
        
        const optionItems = detailsDiv.querySelectorAll('.option-item');
        optionItems.forEach(item => {
            const optionValue = item.getAttribute('data-value');
            if (selectedValues.includes(optionValue)) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }
    
    /**
     * Update option styling based on current final value
     */
    updateOptionStylingFromFinalValue(questionId) {
        const input = document.querySelector(`#final-${questionId} textarea`);
        let selectedValues = [];
        
        // Try to get actual value from data attribute first
        if (input) {
            try {
                const actualValue = JSON.parse(input.getAttribute('data-actual-value') || 'null');
                if (actualValue !== null) {
                    if (Array.isArray(actualValue)) {
                        selectedValues = actualValue;
                    } else {
                        selectedValues = [String(actualValue)];
                    }
                }
            } catch (e) {
                // Fallback to using conflictData (with safe access)
                const finalValue = this.conflictData.final_data?.[questionId] || '';
                if (finalValue) {
                    if (typeof finalValue === 'string') {
                        selectedValues = finalValue.split(',').map(v => v.trim()).filter(v => v);
                    } else if (Array.isArray(finalValue)) {
                        selectedValues = finalValue;
                    } else {
                        selectedValues = [String(finalValue)];
                    }
                }
            }
        } else {
            // Fallback if input not found (with safe access)
            const finalValue = this.conflictData.final_data?.[questionId] || '';
            if (finalValue) {
                if (typeof finalValue === 'string') {
                    selectedValues = finalValue.split(',').map(v => v.trim()).filter(v => v);
                } else if (Array.isArray(finalValue)) {
                    selectedValues = finalValue;
                } else {
                    selectedValues = [String(finalValue)];
                }
            }
        }
        
        this.updateOptionStyling(questionId, selectedValues);
    }
    
    /**
     * Task 4.3: Final Outcome Editing Functionality
     * Direct text input editing for final outcomes
     * Auto-save functionality with visual feedback
     * Input validation and error handling
     * Auto-fill dependent questions when parent questions change
     */
    async updateFinalOutcome(questionId, value) {
        const finalDiv = document.getElementById(`final-${questionId}`);
        const saveIndicator = document.getElementById(`save-${questionId}`);
        const input = finalDiv.querySelector('textarea');
        
        // Check if value is empty (no response selected)
        const isEmpty = value === null || value === undefined || value === '' || 
                       (Array.isArray(value) && value.length === 0);
        
        // If empty, send DELETE instead of PUT
        if (isEmpty) {
            // Mark as modified
            finalDiv.classList.add('modified');
            
            try {
                const response = await fetch(`/api/conflicts/${this.paperId}/${questionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    const responseData = await response.json();
                    
                    // Show save indicator with visual feedback
                    saveIndicator.classList.add('show');
                    saveIndicator.textContent = '✓ Removed';
                    saveIndicator.style.color = '#6c757d';
                    
                    setTimeout(() => {
                        saveIndicator.classList.remove('show');
                        finalDiv.classList.remove('modified');
                    }, 2000);
                    
                    // Remove from local data (with safe access)
                    if (this.conflictData.final_data) {
                        delete this.conflictData.final_data[questionId];
                    }
                    
                    // Update placeholder
                    input.placeholder = 'No response (removed)';
                    
                    // Check if this question change should trigger dependent question auto-fill
                    await this.handleDependentQuestions(questionId, value);
                    
                    // Update row styling for the current question
                    this.updateQuestionRowStyling(questionId);
                    
                    // If this was a comment field, also update the base question styling
                    if (responseData.base_question_id) {
                        this.updateQuestionRowStyling(responseData.base_question_id);
                    }
                    
                    // Update progress tracking
                    this.updateProgress();
                    
                    // If hideResolved is enabled and this question is now resolved, hide it
                    if (this.hideResolved && !this.showAllQuestions) {
                        const questionRow = document.getElementById(`question-${questionId}`);
                        const hasConflict = this.conflictData.conflicts.includes(questionId) || 
                                          (this.conflictData.comment_conflicts && 
                                           this.conflictData.comment_conflicts.includes(questionId));
                        
                        if (hasConflict && questionRow) {
                            // Clear any existing timeout for this question
                            if (this.hideTimeouts.has(questionId)) {
                                clearTimeout(this.hideTimeouts.get(questionId));
                            }
                            
                            const timeoutId = setTimeout(() => {
                                if (this.hideResolved && !this.showAllQuestions && questionRow) {
                                    questionRow.style.display = 'none';
                                }
                                this.hideTimeouts.delete(questionId);
                            }, 500);
                            
                            this.hideTimeouts.set(questionId, timeoutId);
                        }
                    }
                } else {
                    const errorData = await response.json();
                    const errorMessage = errorData.error || 'Unknown error occurred';
                    this.showSaveError(saveIndicator, errorMessage);
                    finalDiv.classList.remove('modified');
                    console.error('Server error:', errorData);
                }
                
            } catch (error) {
                console.error('Network error removing final outcome:', error);
                let errorMessage = 'Network error. Please check your connection and try again.';
                if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    errorMessage = 'Unable to connect to server. Please try again later.';
                }
                this.showSaveError(saveIndicator, errorMessage);
                finalDiv.classList.remove('modified');
            }
            
            return; // Exit early for DELETE case
        }
        
        // Validate input before sending (only for non-empty values)
        const validationError = this.validateInput(value, questionId);
        if (validationError) {
            this.showValidationError(input, validationError);
            return;
        }
        
        // Clear any previous validation errors
        this.clearValidationError(input);
        
        // Mark as modified
        finalDiv.classList.add('modified');
        
        try {
            const response = await fetch(`/api/conflicts/${this.paperId}/${questionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ value: value })
            });
            
            if (response.ok) {
                const responseData = await response.json();
                
                // Show save indicator with visual feedback
                saveIndicator.classList.add('show');
                saveIndicator.textContent = '✓ Saved';
                saveIndicator.style.color = '#28a745';
                
                setTimeout(() => {
                    saveIndicator.classList.remove('show');
                    finalDiv.classList.remove('modified');
                }, 2000);
                
                // Update local data
                if (!this.conflictData.final_data) {
                    this.conflictData.final_data = {};
                }
                this.conflictData.final_data[questionId] = value;
                
                // Check if this question change should trigger dependent question auto-fill
                await this.handleDependentQuestions(questionId, value);
                
                // Update row styling for the current question
                this.updateQuestionRowStyling(questionId);
                
                // If this was a comment field, also update the base question styling
                if (responseData.base_question_id) {
                    this.updateQuestionRowStyling(responseData.base_question_id);
                }
                
                // Update progress tracking
                this.updateProgress();
                
                // If hideResolved is enabled and this question is now resolved, hide it
                if (this.hideResolved && !this.showAllQuestions) {
                    const questionRow = document.getElementById(`question-${questionId}`);
                    const hasConflict = this.conflictData.conflicts.includes(questionId) || 
                                      (this.conflictData.comment_conflicts && 
                                       this.conflictData.comment_conflicts.includes(questionId));
                    const isResolved = value !== '' && value !== null && value !== undefined;
                    
                    if (hasConflict && isResolved && questionRow) {
                        // Clear any existing timeout for this question
                        if (this.hideTimeouts.has(questionId)) {
                            clearTimeout(this.hideTimeouts.get(questionId));
                        }
                        
                        // Check if this is a multi-select question (checkbox)
                        const metadata = this.questionMetadataCache[questionId];
                        const isMultiSelect = metadata && metadata.type === 'checkbox';
                        
                        // Use different delays: 2s for multi-select, 500ms for single-select
                        const delay = isMultiSelect ? 2000 : 500;
                        
                        const timeoutId = setTimeout(() => {
                            // Re-check if still resolved and hideResolved is still enabled
                            if (this.hideResolved && !this.showAllQuestions) {
                                const currentValue = this.conflictData.final_data?.[questionId];
                                const stillResolved = currentValue !== '' && currentValue !== null && currentValue !== undefined;
                                if (stillResolved && questionRow) {
                                    questionRow.style.display = 'none';
                                }
                            }
                            // Clean up the timeout reference
                            this.hideTimeouts.delete(questionId);
                        }, delay);
                        
                        // Store the timeout reference
                        this.hideTimeouts.set(questionId, timeoutId);
                    }
                }
            } else {
                const errorData = await response.json();
                const errorMessage = errorData.error || 'Unknown error occurred';
                
                // Show user-friendly error message
                this.showSaveError(saveIndicator, errorMessage);
                finalDiv.classList.remove('modified');
                
                // Log detailed error for debugging
                console.error('Server error:', errorData);
            }
            
        } catch (error) {
            console.error('Network error updating final outcome:', error);
            
            let errorMessage = 'Network error. Please check your connection and try again.';
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = 'Unable to connect to server. Please try again later.';
            }
            
            this.showSaveError(saveIndicator, errorMessage);
            finalDiv.classList.remove('modified');
        }
    }
    
    /**
     * Handle dependent questions when a parent question changes
     */
    async handleDependentQuestions(parentQuestionId, parentValue) {
        // Define the dependency rules based on the survey schema
        const dependencyRules = {
            '31-q-p2-setup-implementation-2-browserbased': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '32-q-p2-setup-implementation-3-automation',
                    '34-q-p2-setup-implementation-5-browserused',
                    '35-q-p2-setup-implementation-6-browserversion',
                    '36-q-p2-setup-implementation-6-browserinstrumentation',
                    '37-q-p2-setup-implementation-7-browserext',
                    '38-q-p2-setup-implementation-8-headless',
                    '39-q-p2-setup-implementation-9-dimensions',
                    '40-q-p2-setup-implementation-10-incognito',
                    '62-q-p2-process-5-pageinteraction'
                ]
            },
            '24-q-p2-dataset-webpage-2-internal': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '25-q-p2-dataset-webpage-3-internalselection',
                    '26-q-p2-dataset-webpage-4-internalsize',
                    '26-27-q-p2-dataset-webpage-4-internalsize-details',
                    '28-q-p2-dataset-webpage-5-internallock',
                    '29-q-p2-dataset-webpage-6-robots'
                ]
            },
            '76-q-p3-factors-1-factors': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '77-q-p3-factors-2-factorsloc',
                    '78-q-p3-factors-3-factorscat',
                    '79-q-p3-factors-4-dataset',
                    '80-q-p3-factors-5-implementation',
                    '81-q-p3-factors-6-env',
                    '82-q-p3-factors-7-process',
                    '83-q-p3-factors-8-reporting',
                    '84-q-p3-factors-9-other'
                ]
            },
           '85-q-p3-factortesting-1-testing': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '86-q-p3-factortesting-2-which',
                    '87-q-p3-factortesting-3-core'
                ]
            },
            '95-q-p4-practices-7-code': {
                condition: (value) => !['Yes', 'Partially', 'Dead link', 'Empty repo'].includes(value),
                dependentQuestions: [
                    '97-q-p4-practices-9-codewhere'
                ]
            },
            '96-q-p4-practices-8-data': {
                condition: (value) => !['Yes', 'Partially', 'Dead link', 'Empty repo'].includes(value),
                dependentQuestions: [
                    '98-q-p4-practices-10-datawhere'
                ]
            },
            '12-q-p1-major-5-datasetsource': {
                'condition': (value) => !['DB/Archive'].includes(value),
                dependentQuestions: [
                    '13-q-p1-major-6-datasetused'
                ]
            },
            '60-q-p2-process-4-pagestay': {
                'condition': (value) => !['specified'].includes(value),
                dependentQuestions: [
                    '60-61-q-p2-process-4-pagestay-seconds'
                ]
            }
            // Add more dependency rules as needed
        };
        
        const rule = dependencyRules[parentQuestionId];
        if (!rule) {
            return; // No dependency rule for this question
        }

        const normalizedParentValue = this.normalizeDependencyValue(parentValue);
        if (this.shouldDebugDependencies()) {
            console.debug('[conflict-debug] dependency check', {
                phase: 'handleDependentQuestions',
                parentQuestionId,
                rawParentValue: parentValue,
                normalizedParentValue,
                rule
            });
        }
        
        if (rule.condition(normalizedParentValue)) {
            // Parent condition is met, remove dependent questions from final result
            let removedCount = 0;
            let failedCount = 0;
            
            for (const dependentQuestionId of rule.dependentQuestions) {
                // Always try to remove dependent questions when parent condition is met
                // Don't skip based on current value - we want to ensure they're removed
                                
                // Delete the entry to indicate "not applicable" - completely remove from final result
                try {
                    const response = await fetch(`/api/conflicts/${this.paperId}/${dependentQuestionId}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        // Remove from local data
                        if (this.conflictData.final_data) {
                            delete this.conflictData.final_data[dependentQuestionId];
                        }
                        
                        // Update the input field if it's visible to show "No response"
                        const dependentInput = document.querySelector(`#final-${dependentQuestionId} textarea`);
                        if (dependentInput) {
                            dependentInput.value = '';
                            dependentInput.placeholder = 'No response (removed)';
                        }
                        
                        // Update row styling
                        this.updateQuestionRowStyling(dependentQuestionId);
                        
                        // If hideResolved is enabled, hide the dependent question too
                        if (this.hideResolved && !this.showAllQuestions) {
                            const questionRow = document.getElementById(`question-${dependentQuestionId}`);
                            if (questionRow) {
                                // Clear any existing timeout for this question
                                if (this.hideTimeouts.has(dependentQuestionId)) {
                                    clearTimeout(this.hideTimeouts.get(dependentQuestionId));
                                }
                                
                                // Hide after a short delay
                                const timeoutId = setTimeout(() => {
                                    if (this.hideResolved && !this.showAllQuestions && questionRow) {
                                        questionRow.style.display = 'none';
                                    }
                                    // Clean up the timeout reference
                                    this.hideTimeouts.delete(dependentQuestionId);
                                }, 500);
                                
                                // Store the timeout reference
                                this.hideTimeouts.set(dependentQuestionId, timeoutId);
                            }
                        }

                    } else {
                        failedCount++;
                        console.log(`Failed to remove ${dependentQuestionId} from final result`);
                    }
                } catch (error) {
                    failedCount++;
                    console.error(`Error removing dependent question ${dependentQuestionId}:`, error);
                }
            }
            
            if (removedCount > 0 || failedCount > 0) {
                // Show notification about removed questions
                this.showAutoFillNotification(parentQuestionId, removedCount, failedCount);
            }
        }
    }
    
    /**
     * Show notification about removed dependent questions
     */
    showAutoFillNotification(parentQuestionId, successCount, failedCount) {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.className = 'auto-fill-notification';
        
        let message = `Removed ${successCount} dependent question${successCount !== 1 ? 's' : ''} from final result`;
        if (failedCount > 0) {
            message += ` (${failedCount} failed to remove)`;
        }
        
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">🗑️</span>
                <span class="notification-text">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Add to the page
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    /**
     * Get the number of questions that depend on this question
     */
    getDependentQuestionCount(questionId) {
        const dependencyRules = {
            '31-q-p2-setup-implementation-2-browserbased': {
                dependentQuestions: [
                    '32-q-p2-setup-implementation-3-automation',
                    '34-q-p2-setup-implementation-5-browserused',
                    '35-q-p2-setup-implementation-6-browserversion',
                    '36-q-p2-setup-implementation-6-browserinstrumentation',
                    '37-q-p2-setup-implementation-7-browserext',
                    '38-q-p2-setup-implementation-8-headless',
                    '39-q-p2-setup-implementation-9-dimensions',
                    '40-q-p2-setup-implementation-10-incognito',
                    '62-q-p2-process-5-pageinteraction'
                ]
            },
            '24-q-p2-dataset-webpage-2-internal': {
                dependentQuestions: [
                    '25-q-p2-dataset-webpage-3-internalselection',
                    '26-q-p2-dataset-webpage-4-internalsize',
                    '26-27-q-p2-dataset-webpage-4-internalsize-details',
                    '28-q-p2-dataset-webpage-5-internallock',
                    '29-q-p2-dataset-webpage-6-robots'
                ]
            },
            '76-q-p3-factors-1-factors': {
                dependentQuestions: [
                    '77-q-p3-factors-2-factorsloc',
                    '78-q-p3-factors-3-factorscat',
                    '79-q-p3-factors-4-dataset',
                    '80-q-p3-factors-5-implementation',
                    '81-q-p3-factors-6-env',
                    '82-q-p3-factors-7-process',
                    '83-q-p3-factors-8-reporting',
                    '84-q-p3-factors-9-other'
                ]
            }, 
            '85-q-p3-factortesting-1-testing': {
                dependentQuestions: [
                    '86-q-p3-factortesting-2-which',
                    '87-q-p3-factortesting-3-core'
                ]
            }
        };
        
        const rule = dependencyRules[questionId];
        return rule ? rule.dependentQuestions.length : 0;
    }
    
    /**
     * Get the parent question that this question depends on
     */
    getParentQuestion(questionId) {
        const dependencyRules = {
            '31-q-p2-setup-implementation-2-browserbased': {
                dependentQuestions: [
                    '32-q-p2-setup-implementation-3-automation',
                    '34-q-p2-setup-implementation-5-browserused',
                    '35-q-p2-setup-implementation-6-browserversion',
                    '36-q-p2-setup-implementation-6-browserinstrumentation',
                    '37-q-p2-setup-implementation-7-browserext',
                    '38-q-p2-setup-implementation-8-headless',
                    '39-q-p2-setup-implementation-9-dimensions',
                    '40-q-p2-setup-implementation-10-incognito',
                    '62-q-p2-process-5-pageinteraction'
                ]
            },
            '24-q-p2-dataset-webpage-2-internal': {
                dependentQuestions: [
                    '25-q-p2-dataset-webpage-3-internalselection',
                    '26-q-p2-dataset-webpage-4-internalsize',
                    '26-27-q-p2-dataset-webpage-4-internalsize-details',
                    '28-q-p2-dataset-webpage-5-internallock',
                    '29-q-p2-dataset-webpage-6-robots'
                ]
            },
            '76-q-p3-factors-1-factors': {
                dependentQuestions: [
                    '77-q-p3-factors-2-factorsloc',
                    '78-q-p3-factors-3-factorscat',
                    '79-q-p3-factors-4-dataset',
                    '80-q-p3-factors-5-implementation',
                    '81-q-p3-factors-6-env',
                    '82-q-p3-factors-7-process',
                    '83-q-p3-factors-8-reporting',
                    '84-q-p3-factors-9-other'
                ]
            },
            '85-q-p3-factortesting-1-testing': {
                dependentQuestions: [
                    '86-q-p3-factortesting-2-which',
                    '87-q-p3-factortesting-3-core'
                ]
            }
        };
        
        // Find which parent question this question depends on
        for (const [parentQuestionId, rule] of Object.entries(dependencyRules)) {
            if (rule.dependentQuestions.includes(questionId)) {
                return parentQuestionId;
            }
        }
        
        return null;
    }

    validateInput(value, questionId) {
        // Basic client-side validation
        if (value === null || value === undefined) {
            return null; // Allow empty values for now
        }
        
        // Check for extremely long values
        if (typeof value === 'string' && value.length > 10000) {
            return 'Input is too long (maximum 10,000 characters)';
        }
        
        // Check for array values that might be incorrectly formatted
        if (Array.isArray(value) && value.length > 100) {
            return 'Too many options selected (maximum 100)';
        }
        
        return null;
    }
    
    showValidationError(input, message) {
        // Remove any existing error
        this.clearValidationError(input);
        
        // Add error styling
        input.classList.add('validation-error');
        
        // Create error message element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'validation-error-message';
        errorDiv.textContent = message;
        
        // Insert error message after input
        input.parentNode.insertBefore(errorDiv, input.nextSibling);
        
        // Auto-remove error after 5 seconds
        setTimeout(() => {
            this.clearValidationError(input);
        }, 5000);
    }
    
    clearValidationError(input) {
        input.classList.remove('validation-error');
        
        const errorDiv = input.parentNode.querySelector('.validation-error-message');
        if (errorDiv) {
            errorDiv.remove();
        }
    }
    
    showSaveError(saveIndicator, message) {
        saveIndicator.classList.add('show');
        saveIndicator.textContent = '✗ Error';
        saveIndicator.style.color = '#dc3545';
        
        // Show detailed error in tooltip or alert
        saveIndicator.title = message;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            saveIndicator.classList.remove('show');
            saveIndicator.title = '';
        }, 5000);
    }
    
    /**
     * Task 4.4: Progress Tracking and Visual Indicators
     * Update conflict resolution counters
     * Highlight unresolved conflicts
     * Show completion indicators
     */
    updateProgress() {
        if (!this.conflictData) return;
        
        const totalConflicts = this.conflictData.conflicts.length;
        const resolvedCount = this.calculateResolvedCount();
        
        // Update progress counters (Requirements 6.1, 6.2)
        document.getElementById('total-conflicts').textContent = totalConflicts;
        document.getElementById('resolved-count').textContent = resolvedCount;
        
        // Update progress bar with smooth animation
        const percentage = totalConflicts > 0 ? (resolvedCount / totalConflicts) * 100 : 0;
        const progressFill = document.getElementById('progress-fill');
        progressFill.style.width = `${percentage}%`;
        
        // Update progress bar color based on completion
        if (percentage === 100) {
            progressFill.style.backgroundColor = '#28a745'; // Green for complete
        } else if (percentage >= 50) {
            progressFill.style.backgroundColor = '#ffc107'; // Yellow for in progress
        } else {
            progressFill.style.backgroundColor = '#dc3545'; // Red for minimal progress
        }
        
        // Show completion indicator (Requirement 6.3)
        const statusSpan = document.getElementById('completion-status');
        if (resolvedCount === totalConflicts && totalConflicts > 0) {
            statusSpan.textContent = '✓ All conflicts resolved!';
            statusSpan.style.color = '#28a745';
            statusSpan.style.fontWeight = 'bold';
            statusSpan.classList.add('completion-indicator');
            
            // Add celebration animation
            statusSpan.style.animation = 'pulse 2s ease-in-out';
        } else if (totalConflicts > 0) {
            const remaining = totalConflicts - resolvedCount;
            statusSpan.textContent = `${remaining} conflict${remaining !== 1 ? 's' : ''} remaining`;
            statusSpan.style.color = '#6c757d';
            statusSpan.style.fontWeight = 'normal';
            statusSpan.classList.remove('completion-indicator');
            statusSpan.style.animation = '';
        } else {
            statusSpan.textContent = '';
            statusSpan.style.animation = '';
        }
        
        // Highlight unresolved conflicts (Requirement 6.4)
        this.highlightUnresolvedConflicts();
        
        // Update document title with progress
        this.updateDocumentTitle(resolvedCount, totalConflicts);
        
        // Always auto-expand top-most field when in hideResolved mode
        if (this.hideResolved) {
            const firstUnresolved = Array.from(document.getElementById('questions-list').children)
                .find(el => el.tagName === 'DIV' && !el.classList.contains('resolved') && el.classList.contains('conflict'));
            if (firstUnresolved) {
                conflictManager.toggleQuestionDetails(firstUnresolved.id.slice(9));
            }
        }

    }
    
    calculateResolvedCount() {
        if (!this.conflictData) return 0;
        
        if (this.mode === 'initial') {
            // Count questions with initial resolution decisions
            const resolutions = this.conflictData.initial_resolutions || {};
            return Object.keys(resolutions).filter(qId => resolutions[qId] !== '').length;
        } else {
            // Existing final resolution logic
            if (!this.conflictData.final_data) {
                return 0;
            }
            return this.conflictData.conflicts.filter(questionId => {
                const value = this.conflictData.final_data[questionId];
                return this.isQuestionResolved(questionId, value);
            }).length;
        }
    }
    
    highlightUnresolvedConflicts() {
        if (!this.conflictData) return;
        
        // Update styling for all visible questions
        const questionsToCheck = this.showAllQuestions ? 
            (this.conflictData.all_questions || []) : 
            this.conflictData.conflicts;
            
        questionsToCheck.forEach(questionId => {
            this.updateQuestionRowStyling(questionId);
        });
    }
    
    isQuestionResolved(questionId, value) {
        if (questionId.endsWith('-Comment')) {
            return true;
        }
        // Check if this question was removed due to dependency rules
        if (this.isQuestionRemovedByDependency(questionId)) {
            return true; // Consider removed questions as resolved
        }
        
        if (value === null || value === undefined || value === '') {
            return false;
        }
        if (Array.isArray(value) && value.length === 0) {
            return false;
        }
        return true;
    }
    
    /**
     * Check if a question was removed due to dependency rules
     */
    isQuestionRemovedByDependency(questionId) {
        // In initial resolution mode, dependency removal doesn't apply
        if (this.mode === 'initial') {
            return false;
        }
        
        // Check if final_data exists
        if (!this.conflictData || !this.conflictData.final_data) {
            return false;
        }
        
        // Define the same dependency rules as in handleDependentQuestions
        const dependencyRules = {
            '31-q-p2-setup-implementation-2-browserbased': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '32-q-p2-setup-implementation-3-automation',
                    '34-q-p2-setup-implementation-5-browserused',
                    '35-q-p2-setup-implementation-6-browserversion',
                    '36-q-p2-setup-implementation-6-browserinstrumentation',
                    '37-q-p2-setup-implementation-7-browserext',
                    '38-q-p2-setup-implementation-8-headless',
                    '39-q-p2-setup-implementation-9-dimensions',
                    '40-q-p2-setup-implementation-10-incognito',
                    '62-q-p2-process-5-pageinteraction'
                ]
            },
            '24-q-p2-dataset-webpage-2-internal': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '25-q-p2-dataset-webpage-3-internalselection',
                    '26-q-p2-dataset-webpage-4-internalsize',
                    '26-27-q-p2-dataset-webpage-4-internalsize-details',
                    '28-q-p2-dataset-webpage-5-internallock',
                    '29-q-p2-dataset-webpage-6-robots'
                ]
            },
            '76-q-p3-factors-1-factors': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '77-q-p3-factors-2-factorsloc',
                    '78-q-p3-factors-3-factorscat',
                    '79-q-p3-factors-4-dataset',
                    '80-q-p3-factors-5-implementation',
                    '81-q-p3-factors-6-env',
                    '82-q-p3-factors-7-process',
                    '83-q-p3-factors-8-reporting',
                    '84-q-p3-factors-9-other'
                ]
            },
            '85-q-p3-factortesting-1-testing': {
                condition: (value) => value === false || value === 'false' || value === 'No',
                dependentQuestions: [
                    '86-q-p3-factortesting-2-which',
                    '87-q-p3-factortesting-3-core'
                ]
            },
            // Question 69 controls question 70
            '69-q-p2-crawlmultiple-1-multiple': {
                condition: (value) => {
                    const numValue = parseInt(value);
                    return isNaN(numValue) || numValue <= 1;
                },
                dependentQuestions: [
                    '70-q-p2-crawlmultiple-2-multipledetails'
                ]
            },
            // Question 78 controls questions 79-84 (multi-select)
            '78-q-p3-factors-3-factorscat': {
                type: 'multiselect',
                dependentQuestions: {
                    '79-q-p3-factors-4-dataset': 'Dataset',
                    '80-q-p3-factors-5-implementation': 'Crawler Implementation',
                    '81-q-p3-factors-6-env': 'Crawling Environment',
                    '82-q-p3-factors-7-process': 'Crawling Setup',
                    '83-q-p3-factors-8-reporting': 'Analysis & Reporting',
                    '84-q-p3-factors-9-other': 'Other/Ungrouped'
                }
            },
            '95-q-p4-practices-7-code': {
                condition: (value) => !['Yes', 'Partially', 'Dead link', 'Empty repo'].includes(value),
                dependentQuestions: [
                    '97-q-p4-practices-9-codewhere'
                ]
            },
            '96-q-p4-practices-8-data': {
                condition: (value) => !['Yes', 'Partially', 'Dead link', 'Empty repo'].includes(value),
                dependentQuestions: [
                    '98-q-p4-practices-10-datawhere'
                ]
            },
            '12-q-p1-major-5-datasetsource': {
                'condition': (value) => !['DB/Archive'].includes(value),
                dependentQuestions: [
                    '13-q-p1-major-6-datasetused'
                ]
            },
            '60-q-p2-process-4-pagestay': {
                'condition': (value) => !['specified'].includes(value),
                dependentQuestions: [
                    '60-61-q-p2-process-4-pagestay-seconds'
                ]
            }
        };
        
        // Check if this question is a dependent of any parent question
        for (const [parentQuestionId, rule] of Object.entries(dependencyRules)) {
            if (rule.type === 'multiselect') {
                // Handle multi-select dependencies (question 78)
                if (questionId in rule.dependentQuestions) {
                    const parentValue = this.conflictData.final_data[parentQuestionId];
                    const requiredValue = rule.dependentQuestions[questionId];

                    if (parentValue === undefined || parentValue === null || parentValue === '' ||
                        (Array.isArray(parentValue) && parentValue.length === 0)) {
                        return false; // Parent not resolved yet, so dependent is not removed
                    }
                    
                    // Convert parent value to array if needed
                    const parentArray = Array.isArray(parentValue) ? parentValue : 
                                      (parentValue ? [parentValue] : []);
                    
                    // If required value is NOT in parent array, question should be removed
                    if (!parentArray.includes(requiredValue)) {
                        return true;
                    }
                }
            } else {
                // Handle standard binary dependencies
                if (rule.dependentQuestions.includes(questionId)) {
                    // Check if the parent question has the condition that would remove this question
                    const parentValue = this.conflictData.final_data[parentQuestionId];
                    const normalizedParentValue = this.normalizeDependencyValue(parentValue);
                    if (this.shouldDebugDependencies()) {
                        console.debug('[conflict-debug] dependency check', {
                            phase: 'isQuestionRemovedByDependency',
                            questionId,
                            parentQuestionId,
                            rawParentValue: parentValue,
                            normalizedParentValue,
                            rule
                        });
                    }

                    if (normalizedParentValue === undefined || normalizedParentValue === null || normalizedParentValue === '' ||
                        (Array.isArray(normalizedParentValue) && normalizedParentValue.length === 0)) {
                        return false; // Parent not resolved yet, so dependent is not removed
                    }
                    if (rule.condition(normalizedParentValue)) {
                        return true; // This question should be considered resolved (removed)
                    }
                }
            }
        }
        
        return false;
    }

    normalizeDependencyValue(value) {
        if (Array.isArray(value) && value.length === 1) {
            return value[0];
        }
        return value;
    }

    shouldDebugDependencies() {
        try {
            return localStorage.getItem('conflictDebugDependencies') === '1' ||
                   new URLSearchParams(window.location.search).get('debugDependencies') === '1';
        } catch (error) {
            return false;
        }
    }
    
    updateQuestionRowStyling(questionId) {
        const questionRow = document.getElementById(`question-${questionId}`);
        if (!questionRow) return;
        
        const hasConflict = this.conflictData.conflicts.includes(questionId);
        const hasCommentConflict = this.conflictData.comment_conflicts && 
                                 this.conflictData.comment_conflicts.includes(`${questionId}-Comment`);
        
        let isResolved = false;
        
        if (this.mode === 'initial') {
            // In initial resolution mode, check if decision has been made
            const resolutions = this.conflictData.initial_resolutions || {};
            isResolved = resolutions[questionId] && resolutions[questionId] !== '';
        } else {
            // In final resolution mode, check final value
            const finalValue = this.conflictData.final_data?.[questionId];
            isResolved = this.isQuestionResolved(questionId, finalValue);
        }
        
        // Remove all status classes first
        questionRow.classList.remove('conflict', 'resolved', 'agreement', 'unresolved-highlight', 'comment-conflict');
        
        // Apply appropriate classes
        if (hasConflict) {
            if (isResolved) {
                questionRow.classList.add('resolved');
            } else {
                questionRow.classList.add('conflict', 'unresolved-highlight');
            }
        } else {
            questionRow.classList.add('agreement');
        }
        
        if (hasCommentConflict) {
            questionRow.classList.add('comment-conflict');
        }
        
        // Update resolution indicators
        if (isResolved) {
            if (this.mode === 'initial') {
                // In initial mode, use the special initial indicator
                const resolutions = this.conflictData.initial_resolutions || {};
                const decision = resolutions[questionId];
                this.addResolvedIndicatorForInitial(questionRow, questionId, decision);
            } else {
                this.addResolvedIndicator(questionRow, questionId);
            }
        } else if (hasConflict) {
            this.addUnresolvedIndicator(questionRow, questionId);
        }
    }
    
    addResolvedIndicator(questionRow, questionId) {
        // Check if this question was resolved by dependency removal
        const wasRemovedByDependency = this.isQuestionRemovedByDependency(questionId);
        
        // Add appropriate indicator for resolved questions
        let indicator = questionRow.querySelector('.resolution-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            const questionHeader = questionRow.querySelector('.question-header');
            if (questionHeader) {
                questionHeader.appendChild(indicator);
            }
        }
        
        if (wasRemovedByDependency) {
            // Special indicator for questions removed due to dependencies
            indicator.className = 'resolution-indicator removed-indicator';
            indicator.innerHTML = '🗑️';
            indicator.title = 'Question removed (not applicable)';
            // Update the input field if it's visible to show "No response"
            const dependentInput = questionRow.querySelector('.final-outcome textarea');
            dependentInput.placeholder = 'No response (removed)';
        } else {
            // Regular resolved indicator
            indicator.className = 'resolution-indicator resolved-indicator';
            indicator.innerHTML = '✓';
            indicator.title = 'Conflict resolved';
        }
    }
    
    addUnresolvedIndicator(questionRow, questionId) {
        // Add warning indicator for unresolved conflicts
        let indicator = questionRow.querySelector('.resolution-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'resolution-indicator unresolved-indicator';
            indicator.innerHTML = '⚠';
            indicator.title = 'Conflict needs resolution';
            
            const questionHeader = questionRow.querySelector('.question-header');
            if (questionHeader) {
                questionHeader.appendChild(indicator);
            }
        }
        indicator.className = 'resolution-indicator unresolved-indicator';
        indicator.innerHTML = '⚠';
        indicator.title = 'Conflict needs resolution';
    }
    
    updateDocumentTitle(resolvedCount, totalConflicts) {
        // Update browser tab title with progress
        const baseTitle = `Resolve Conflicts - Paper ${this.paperId}`;
        if (totalConflicts > 0) {
            const percentage = Math.round((resolvedCount / totalConflicts) * 100);
            document.title = `(${percentage}%) ${baseTitle}`;
        } else {
            document.title = baseTitle;
        }
    }
    
    async loadConflictData() {
        const questionsContainer = document.getElementById('questions-list');
        
        try {
            questionsContainer.innerHTML = '<div class="loading">Loading conflict data...</div>';
            
            // Use different API endpoint based on mode
            const apiUrl = this.mode === 'initial' 
                ? `/api/initial-conflicts/${this.paperId}?coder=${encodeURIComponent(this.coderName)}`
                : `/api/conflicts/${this.paperId}`;
            
            const response = await fetch(apiUrl);
            
            if (!response.ok) {
                let errorMessage = 'Failed to load conflict data';
                
                if (response.status === 404) {
                    errorMessage = 'Paper not found or has no responses';
                } else if (response.status === 500) {
                    errorMessage = 'Server error loading conflict data';
                } else {
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (e) {
                        // Use default message if can't parse error
                    }
                }
                
                throw new Error(errorMessage);
            }
            
            this.conflictData = await response.json();
            
            // Validate received data
            if (!this.conflictData || typeof this.conflictData !== 'object') {
                throw new Error('Invalid conflict data received from server');
            }
            
            if (!this.conflictData.coder_data || Object.keys(this.conflictData.coder_data).length < 2) {
                throw new Error('Insufficient coder data - need at least 2 coders');
            }
            
            // Update coder headers
            const coderNames = Object.keys(this.conflictData.coder_data);
            if (coderNames.length >= 2) {
                const coder1Header = document.getElementById('coder1-header');
                const coder2Header = document.getElementById('coder2-header');
                
                if (coder1Header) coder1Header.textContent = coderNames[0];
                if (coder2Header) coder2Header.textContent = coderNames[1];
            }
            
            this.renderQuestions();
            this.updateProgress();
            this.updateViewStatus(); // Initialize view status
            
        } catch (error) {
            console.error('Error loading conflict data:', error);
            
            questionsContainer.innerHTML = `
                <div class="error">
                    <h3>Error Loading Data</h3>
                    <p>${error.message}</p>
                    <button onclick="conflictManager.loadConflictData()" class="retry-btn">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
    
    renderQuestions() {
        const container = document.getElementById('questions-list');
        
        if (!this.conflictData) {
            container.innerHTML = '<div class="loading">Loading...</div>';
            return;
        }
        
        container.innerHTML = '';
        
        const coderNames = Object.keys(this.conflictData.coder_data);
        const coder1Name = coderNames[0];
        const coder2Name = coderNames[1];
        
        // Determine which questions to show
        let questionsToShow = [];
        
        if (this.showAllQuestions) {
            // Show all questions including comment fields as separate entries
            questionsToShow = (this.conflictData.all_questions || []);
        } else {
            // Show only conflicts
            questionsToShow = [...this.conflictData.conflicts];
            
            // For final mode, also include comment conflicts
            if (this.mode === 'final' && this.conflictData.comment_conflicts) {
                for (const commentConflict of this.conflictData.comment_conflicts) {
                    if (!questionsToShow.includes(commentConflict)) {
                        questionsToShow.push(commentConflict);
                    }
                }
            }
            // For initial mode, exclude comment conflicts (already filtered in backend)
        }
        
        // Sort questions numerically
        questionsToShow.sort((a, b) => {
            const aNum = parseInt(a.match(/^(\d+)/)?.[1] || '999999');
            const bNum = parseInt(b.match(/^(\d+)/)?.[1] || '999999');
            if (aNum !== bNum) {
                return aNum - bNum;
            }
            const aIsComment = a.endsWith('-Comment');
            const bIsComment = b.endsWith('-Comment');
            return aIsComment - bIsComment;
        });
        
        if (questionsToShow.length === 0) {
            if (this.showAllQuestions) {
                container.innerHTML = `
                    <div class="no-conflicts">
                        <h3>No Questions Found</h3>
                        <p>No questions available for this paper.</p>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="no-conflicts">
                        <h3>✓ No Conflicts Found</h3>
                        <p>All coders are in agreement for this paper.</p>
                    </div>
                `;
            }
            return;
        }
        
        for (const questionId of questionsToShow) {
            const coder1Value = this.conflictData.coder_data[coder1Name].responses[questionId];
            const coder2Value = this.conflictData.coder_data[coder2Name].responses[questionId];
            
            // Get current value based on mode
            let currentValue = '';
            let isResolved = false;
            
            if (this.mode === 'initial') {
                currentValue = this.conflictData.initial_resolutions?.[questionId] || '';
                isResolved = currentValue !== '';
            } else {
                currentValue = this.conflictData.final_data?.[questionId] ?? '';
                isResolved = this.isQuestionResolved(questionId, currentValue);
            }
            
            const isCommentField = questionId.endsWith('-Comment');
            const hasConflict = this.conflictData.conflicts.includes(questionId);
            
            // Determine row class
            let rowClass = hasConflict ? (isResolved ? 'resolved' : 'conflict') : 'agreement';
            if (isCommentField) {
                rowClass += ' comment-field';
            }
            
            const questionRow = document.createElement('div');
            questionRow.className = `question-row ${rowClass}`;
            questionRow.id = `question-${questionId}`;
            
            // Hide resolved conflicts if hideResolved is enabled
            if (this.hideResolved && !this.showAllQuestions && isResolved) {
                questionRow.style.display = 'none';
            }
            
            // Build question ID HTML
            const questionIdHtml = `
                <div class="question-id" onclick="conflictManager.toggleQuestionDetails('${questionId}')">
                    <span class="expand-icon" id="icon-${questionId}">▶</span>
                    <span>${questionId}</span>
                </div>
            `;
            
            // Build final outcome HTML based on mode
            let finalOutcomeHtml = '';
            let coder1Decision = undefined;
            let coder2Decision = undefined;
            
            if (this.mode === 'initial') {
                // Initial resolution: Show buttons
                const currentDecision = this.conflictData.initial_resolutions?.[questionId];
                finalOutcomeHtml = `
                    <div class="final-outcome" id="final-${questionId}">
                        ${this.renderInitialResolutionButtons(questionId, currentDecision, hasConflict)}
                        <span class="save-indicator" id="save-${questionId}">✓ Saved</span>
                    </div>
                `;
            } else {
                // Final resolution: Show textarea (existing functionality)
                finalOutcomeHtml = `
                    <div class="final-outcome" id="final-${questionId}">
                        <textarea 
                            data-actual-value="${this.escapeHtml(JSON.stringify(currentValue))}"
                            onchange="conflictManager.updateFinalOutcome('${questionId}', this.value)"
                            placeholder="Enter or select final outcome">${this.escapeHtml(this.formatValueForInput(currentValue))}</textarea>
                        <span class="save-indicator" id="save-${questionId}">✓ Saved</span>
                    </div>
                `;
                if (hasConflict) {
                    coder1Decision =
                        this.conflictData.initial_resolutions?.[coder1Name]?.resolutions?.[questionId]?.decision;

                    coder2Decision =
                        this.conflictData.initial_resolutions?.[coder2Name]?.resolutions?.[questionId]?.decision;

                    if (coder1Decision == coder2Decision && coder1Decision != 'Discuss') {
                        console.log(questionId, coder1Decision, coder2Decision);
                        coder1Decision = undefined;
                        coder2Decision = undefined;
                    }
                }   
            }
            

            questionRow.innerHTML = `
                <div class="question-header">
                    ${questionIdHtml}
                    <div class="response-value ${this.mode === 'final' ? 'clickable' : ''}" data-value="${this.escapeHtml(JSON.stringify(coder1Value))}" ${this.mode === 'final' ? `onclick="conflictManager.selectCoderResponse('${questionId}', '${coder1Name}')"` : ''}>
                        ${this.formatValue(coder1Value)}
                    </div>
                    <div class="response-value ${this.mode === 'final' ? 'clickable' : ''}" data-value="${this.escapeHtml(JSON.stringify(coder2Value))}" ${this.mode === 'final' ? `onclick="conflictManager.selectCoderResponse('${questionId}', '${coder2Name}')"` : ''}>
                        ${this.formatValue(coder2Value)}
                    </div>
                    ${finalOutcomeHtml}

                    
                    ${coder1Decision ? `
                    <div></div>
                    <div class="initial-decisions">
                        Initial decision: ${this.escapeHtml(coder1Decision)}
                    </div>
                    <div class="initial-decisions">
                        Initial decision: ${this.escapeHtml(coder2Decision)}
                    </div>
                    ` : ""}
                </div>
                <div class="question-details" id="details-${questionId}"><div class="loading">Loading question details...</div></div>
            `;
            
            container.appendChild(questionRow);
            
            // Add resolution indicators after row is in DOM
            if (this.mode === 'initial') {
                if (isResolved) {
                    this.addResolvedIndicatorForInitial(questionRow, questionId, currentValue);
                } else if (hasConflict) {
                    this.addUnresolvedIndicator(questionRow, questionId);
                }
            } else {
                // Final mode indicators (existing logic)
                if (isResolved) {
                    this.addResolvedIndicator(questionRow, questionId);
                } else if (hasConflict) {
                    this.addUnresolvedIndicator(questionRow, questionId);
                }
            }
        }
    }
    
    // Utility methods
    formatValue(value) {
        if (value === null || value === undefined || value === '') {
            return '<em style="color: #999;">No response</em>';
        }
        if (Array.isArray(value)) {
            const sortedValues = [...value]
                .map(item => String(item))
                .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
            return sortedValues.join(', ');
        }
        if (typeof value === 'object') {
            // Handle object values by converting to JSON or extracting meaningful info
            try {
                if (value.hasOwnProperty('id') && value.hasOwnProperty('title')) {
                    return `${value.id}: ${value.title}`;
                } else if (value.hasOwnProperty('value') && value.hasOwnProperty('text')) {
                    return `${value.value} (${value.text})`;
                } else {
                    return JSON.stringify(value);
                }
            } catch (e) {
                return '[Complex Object]';
            }
        }
        return String(value);
    }
    
    formatValueForInput(value) {
        if (value === null || value === undefined || value === '') {
            return '';
        }
        if (Array.isArray(value)) {
            const sortedValues = [...value]
                .map(item => String(item))
                .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
            return sortedValues.join(', ');
        }
        if (typeof value === 'object') {
            // Handle object values for input fields
            try {
                if (value.hasOwnProperty('id') && value.hasOwnProperty('title')) {
                    return `${value.id}: ${value.title}`;
                } else if (value.hasOwnProperty('value')) {
                    return value.value;
                } else {
                    return JSON.stringify(value);
                }
            } catch (e) {
                return '[Complex Object]';
            }
        }
        return String(value);
    }
    
    escapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }
        const textStr = String(text);
        // Use a more robust escaping method that doesn't truncate at special characters
        return textStr
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}

// Global variable to hold the manager instance
let conflictManager = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // These variables should be set by the template
    if (typeof paperId !== 'undefined' && typeof availableCoders !== 'undefined') {
        // Check if mode is defined (for initial resolution)
        const resolutionMode = typeof mode !== 'undefined' ? mode : 'final';
        const resolverName = typeof coderName !== 'undefined' ? coderName : null;
        const surveySchema = typeof schema !== 'undefined' ? schema : null;
        
        conflictManager = new ConflictResolutionManager(
            paperId, 
            availableCoders, 
            resolutionMode, 
            resolverName, 
            surveySchema
        );
    }
});