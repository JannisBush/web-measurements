from flask import Flask, request, jsonify, render_template
from functools import lru_cache
import copy
import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from conflict_analyzer import ConflictAnalyzer
from question_loader import QuestionLoader
from response_manager import ResponseManager
from initial_resolution_manager import InitialResolutionManager

app = Flask(__name__)

SCHEMA_PATH = Path("data/surveyjson.json")
RESPONSES_DIR = Path("data/responses")
FINAL_RESPONSES_PATH = Path("data/final_responses.json")
INITIAL_RESOLUTIONS_DIR = Path("data/initial_resolutions")
PROGRESS_DIR = Path("data/progress")
CUSTOM_OPTIONS_PATH = Path("data/custom-options.json")
PAPER_SELECTION_PATH = Path("../01-paper-selection/paper_selection.csv")

def get_progress_path(coder_name):
    """Get the progress file path for a specific coder."""
    PROGRESS_DIR.mkdir(exist_ok=True)
    return PROGRESS_DIR / f"progress_{coder_name}.json"

def get_responses_path(coder_name):
    """Get the responses file path for a specific coder."""
    RESPONSES_DIR.mkdir(exist_ok=True)
    return RESPONSES_DIR / f"responses_{coder_name}.json"

def get_all_responses_paths():
    """Get all coder-specific response file paths."""
    if not RESPONSES_DIR.exists():
        return []
    return list(RESPONSES_DIR.glob("responses_*.json"))

@lru_cache(maxsize=512)
def _load_json_cached(path_str, mtime_ns, size):
    with open(path_str) as f:
        return json.load(f)


def load_json(path):
    file_path = Path(path)
    stat = file_path.stat()
    return copy.deepcopy(_load_json_cached(str(file_path), stat.st_mtime_ns, stat.st_size))


@lru_cache(maxsize=512)
def _load_csv_cached(path_str, mtime_ns, size, header, fillna_value):
    frame = pd.read_csv(path_str, header=header)
    if fillna_value is not None:
        frame = frame.fillna(fillna_value)
    return frame


def load_csv(path, header=0, fillna_value=None):
    file_path = Path(path)
    stat = file_path.stat()
    return _load_csv_cached(str(file_path), stat.st_mtime_ns, stat.st_size, header, fillna_value).copy(deep=True)


def _path_signature(path):
    stat = Path(path).stat()
    return (str(Path(path)), stat.st_mtime_ns, stat.st_size)


def _directory_signature(directory, pattern):
    directory_path = Path(directory)
    if not directory_path.exists():
        return ()

    signature = []
    for file_path in sorted(directory_path.glob(pattern)):
        stat = file_path.stat()
        signature.append((str(file_path), stat.st_mtime_ns, stat.st_size))
    return tuple(signature)


@lru_cache(maxsize=512)
def _get_conflicts_data_cached(paper_id, responses_signature, final_signature, initial_signature, schema_signature, custom_options_signature):
    response_manager = ResponseManager(str(RESPONSES_DIR), str(FINAL_RESPONSES_PATH), str(SCHEMA_PATH))
    conflict_analyzer = ConflictAnalyzer(str(CUSTOM_OPTIONS_PATH))
    initial_resolution_manager = InitialResolutionManager(response_manager, str(INITIAL_RESOLUTIONS_DIR), str(CUSTOM_OPTIONS_PATH))

    paper_responses = response_manager.load_paper_responses(paper_id)
    if not paper_responses:
        return {"error": "No responses found for this paper"}, 404

    coder_data = conflict_analyzer.get_coder_responses(paper_responses)
    all_questions = list({q for coder in coder_data.values() for q in coder["responses"].keys()})
    conflicts = conflict_analyzer.find_conflicts(paper_responses)
    comment_conflicts = conflict_analyzer.find_comment_conflicts(paper_responses)
    schema = load_json(SCHEMA_PATH)
    initial_resolutions = initial_resolution_manager.get_all_resolutions(paper_id)
    final_responses = response_manager._load_final_responses()

    has_final_response = str(paper_id) in final_responses
    final_data = final_responses.get(str(paper_id), {}).get("data", {})

    resolved_count = 0
    for question_id in conflicts:
        if question_id in final_data:
            resolved_count += 1
        elif response_manager.is_question_removed_by_dependency(question_id, str(paper_id)):
            resolved_count += 1

    return {
        "paper_id": paper_id,
        "coder_data": coder_data,
        "all_questions": all_questions,
        "schema": schema,
        "final_data": final_data,
        "conflicts": conflicts,
        "comment_conflicts": comment_conflicts,
        "resolved_count": resolved_count,
        "has_final_response": has_final_response,
        "initial_resolutions": initial_resolutions,
    }, 200


@lru_cache(maxsize=512)
def _get_initial_conflicts_data_cached(paper_id, coder_name, responses_signature, initial_signature, schema_signature, custom_options_signature):
    response_manager = ResponseManager(str(RESPONSES_DIR), str(FINAL_RESPONSES_PATH), str(SCHEMA_PATH))
    conflict_analyzer = ConflictAnalyzer(str(CUSTOM_OPTIONS_PATH))
    initial_resolution_manager = InitialResolutionManager(response_manager, str(INITIAL_RESOLUTIONS_DIR), str(CUSTOM_OPTIONS_PATH))

    paper_responses = response_manager.load_paper_responses(paper_id)
    if not paper_responses:
        return {"error": "No responses found for this paper"}, 404

    coder_data = conflict_analyzer.get_coder_responses(paper_responses)
    all_questions = list({q for coder in coder_data.values() for q in coder["responses"].keys()})
    conflicts = conflict_analyzer.find_conflicts(paper_responses)
    conflicts = [c for c in conflicts if not c.endswith('-Comment')]
    schema = load_json(SCHEMA_PATH)

    existing_resolutions = initial_resolution_manager.get_resolutions(paper_id, coder_name)
    initial_resolutions = {}
    for question_id, resolution_data in existing_resolutions.get("resolutions", {}).items():
        initial_resolutions[question_id] = resolution_data.get("decision", "")

    return {
        "paper_id": paper_id,
        "coder_data": coder_data,
        "all_questions": all_questions,
        "schema": schema,
        "conflicts": conflicts,
        "initial_resolutions": initial_resolutions,
        "coder_name": coder_name,
    }, 200

def save_json(data, path):
    def numeric_prefix_key(k):
        match = re.match(r'^(\d+)', k)
        is_comment = k.endswith('-Comment')
        if match:
            # Return (priority, numeric_prefix, is_comment, full_key)
            # is_comment=True (1) sorts after is_comment=False (0)
            return (0, int(match.group(1)), 1 if is_comment else 0, k)
        else:
            return (1, 0, 1 if is_comment else 0, k)

    def sort_dict(d):
        if isinstance(d, dict):
            # Sort this level
            sorted_items = sorted(d.items(), key=lambda item: numeric_prefix_key(item[0]))
            # Recurse into values
            return {k: sort_dict(v) for k, v in sorted_items}
        elif isinstance(d, list):
            # For lists, recurse into elements
            return [sort_dict(item) for item in d]
        else:
            # Return primitive as is
            return d

    sorted_data = sort_dict(data)
    with open(path, "w") as f:
        json.dump(sorted_data, f, indent=2)

def normalize_list(entry):
    result = []
    for item in entry:
        if isinstance(item, str):
            result.extend([x.strip() for x in item.split(",")])
    return list(set(result))

def extract_choices_by_url_names(schema):
    names = []

    def recurse(elements):
        for el in elements:
            if isinstance(el, dict):
                if "choicesByUrl" in el and "name" in el:
                    if "/get_options" in el["choicesByUrl"]["url"]:
                        names.append(el["name"])
                # Handle nested elements (e.g., in panels)
                if "elements" in el:
                    recurse(el["elements"])

    for page in schema.get("pages", []):
        recurse(page.get("elements", []))

    return names

def set_options(data, options):
    updated = False
    additions = {}

    option_keys = extract_choices_by_url_names(load_json(SCHEMA_PATH))
    
    for key, value in data.items():
        if key not in option_keys:
            continue

        # If , is in the submission but it is a single select, accept it but log it here
        if "," in str(value) and not isinstance(value, list):
            print(f"{key}: {value} probably should not be a list!")
        
        if not isinstance(value, list):
            value = [value]

        normalized = normalize_list(value)
        existing = set(item["value"] if isinstance(item, dict) else item for item in options.get(key, []))
        new_items = [{"value": item, "text": item} for item in normalized if item not in existing]

        if new_items:
            options.setdefault(key, []).extend(new_items)
            additions[f"{key}-added"] = new_items
            updated = True

        data[key] = normalized

    return additions, updated

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/schema", methods=["GET"])
def get_schema():
    return jsonify(load_json(SCHEMA_PATH))

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Load options and update
    options = load_json(CUSTOM_OPTIONS_PATH)
    additions, updated = set_options(data, options)

    # If we had additions, merge into data and update the options file
    if updated:
        data.update(additions)
        data = dict(sorted(data.items()))
        save_json(options, CUSTOM_OPTIONS_PATH)

    # Save response
    paper_id = str(data["3-q-p0-paperselect"])
    extractor_name = data["1-q-p0-name"]
    
    # Extract coder name from list if needed
    if isinstance(extractor_name, list):
        extractor_name_str = extractor_name[0]
    else:
        extractor_name_str = extractor_name
    
    submission_time = datetime.now(timezone.utc).isoformat()

    # Get coder-specific responses file
    responses_path = get_responses_path(extractor_name_str)
    
    # Load existing responses for this coder or start fresh
    if responses_path.exists():
        coder_responses = load_json(responses_path)
    else:
        coder_responses = {}

    # Append new entry under correct paper_id
    if paper_id not in coder_responses:
        coder_responses[paper_id] = []
    
    coder_responses[paper_id].append({
        "extractor_name": extractor_name,
        "submission_time": submission_time,
        "data": data
    })

    # Save updated responses for this coder
    save_json(coder_responses, responses_path)

    return jsonify({"status": "ok", "added": additions})

@app.route("/get_options", methods=["GET"])
def get_options():
    key = request.args.get("q")  # e.g., "q-p2-dataset-website-1-list"
    if not key:
        return jsonify({"error": "Missing 'q' parameter"}), 400

    try:
        with open(CUSTOM_OPTIONS_PATH, "r") as f:
            options_dict = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to load data file: {str(e)}"}), 500

    if key not in options_dict:
        return jsonify({"error": f"No entry found for key: {key}"}), 404

    return jsonify(options_dict[key])

@app.route("/get_papers", methods=["GET"])
def get_papers():
    key = request.args.get("type")
    extractor = request.args.get("name")
    papers = load_csv(PAPER_SELECTION_PATH, header=0)
    papers = papers.loc[papers["In-Scope"] == "yes"]
    if extractor not in  ["Test", "other"] and key not in ["in-scope", "sampled"]:
        papers = papers.loc[(papers["Coder 1"] == extractor) | (papers["Coder 2"] == extractor)]
    # Do not show finished papers in "own" mode
    if key == "own":
        responses_path = get_responses_path(extractor)
        if responses_path.exists():
            finished = load_json(responses_path)
            ids = [int(id_) for id_ in finished.keys()]
            papers = papers.loc[~papers["id"].isin(ids)]
    if key == "sampled":
        papers = papers.loc[papers["Coder 1"].notna()]
    if key == "progress":
        progress_path = get_progress_path(extractor)
        if progress_path.exists():
            progress = load_json(progress_path)
            ids = [int(id_) for id_ in progress.keys()]
            papers = papers.loc[papers["id"].isin(ids)]
        else:
            # No progress file exists for this coder, return empty
            papers = papers.loc[papers["id"].isin([])]
    if key == "finished":
        responses_path = get_responses_path(extractor)
        if responses_path.exists():
            finished = load_json(responses_path)
            ids = [int(id_) for id_ in finished.keys()]
            papers = papers.loc[papers["id"].isin(ids)]
        else:
            # No responses file exists for this coder, return empty
            papers = papers.loc[papers["id"].isin([])]
    
    choices = papers[["id", "title"]].rename(columns={"id": "value", "title": "text"}).to_dict(orient="records")
    return jsonify(choices)

@app.route("/get_paper_details", methods=["GET"])
def get_paper_details():
    paper_id = request.args.get("id", "")
    papers = load_csv(PAPER_SELECTION_PATH, header=0, fillna_value="")
    paper = papers.loc[papers["id"] == int(paper_id)].iloc[0]
    data = {
        "id": paper_id,
        "title": paper["title"],
        "authors": paper["author"],
        "conference": paper["conference_name"],
        "year": int(paper["conference_year"]),
        "notes": "",
        "pdf_path": paper["path_pdf"].split("/")[-1]
    }
    return jsonify(data)

@app.route("/save_progress", methods=["PUT"])
def save_progress():
    paper_id = request.args.get("paper_id")
    extractor = request.args.get("extractor")
    data = request.get_json()

    if not paper_id or not extractor:
        return jsonify({"error": "Missing paper_id or extractor"}), 400
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    progress_path = get_progress_path(extractor)
    
    # Load existing progress for this coder or start fresh
    if progress_path.exists():
        progress = load_json(progress_path)
    else:
        progress = {}
    
    progress[paper_id] = data
    save_json(progress, progress_path)

    return jsonify({"message": "Progress saved successfully"})

@app.route("/get_progress", methods=["GET"])
def get_progress():
    paper_id = request.args.get("paper_id")
    extractor = request.args.get("extractor")

    if not paper_id or not extractor:
        return jsonify({"error": "Missing paper_id or extractor"}), 400

    progress_path = get_progress_path(extractor)
    
    # If no progress file exists for this coder, return 404
    if not progress_path.exists():
        return jsonify({"error": "No progress found"}), 404
    
    progress = load_json(progress_path)
    data = progress.get(paper_id)

    if data is None:
        return jsonify({"error": "No progress found"}), 404

    return jsonify(data)


# Conflict Resolution Routes

@app.route("/conflicts")
def conflicts():
    """Main conflict resolution interface - display list of papers with multiple coder responses."""
    try:
        # Check if required files exist
        if not RESPONSES_DIR.exists() or not get_all_responses_paths():
            return render_template("conflicts.html", 
                                 papers=[], 
                                 error=f"No response files found. Please ensure {RESPONSES_DIR} exists and contains response files.")
        
        if not PAPER_SELECTION_PATH.exists():
            return render_template("conflicts.html", 
                                 papers=[], 
                                 error=f"Paper selection file not found. Please ensure {PAPER_SELECTION_PATH} exists.")
        
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        initial_resolution_manager = InitialResolutionManager(response_manager, INITIAL_RESOLUTIONS_DIR, CUSTOM_OPTIONS_PATH)
        papers_with_coders = response_manager.get_all_papers_with_multiple_responses()
        
        if not papers_with_coders:
            return render_template("conflicts.html", 
                                 papers=[], 
                                 message="No papers with multiple coder responses found.")
        
        # Get paper details for display
        papers_df = load_csv(PAPER_SELECTION_PATH, header=0)
        paper_details = []
        
        # Sort paper IDs numerically before processing
        sorted_paper_ids = sorted(papers_with_coders.keys(), key=lambda x: int(x))
        
        for paper_id in sorted_paper_ids:
            coders = papers_with_coders[paper_id]
            try:
                paper_row = papers_df.loc[papers_df["id"] == int(paper_id)]
                if not paper_row.empty:
                    paper_info = paper_row.iloc[0]
                    
                    # Get initial resolution status
                    resolution_status = initial_resolution_manager.get_resolution_status(paper_id)
                    
                    paper_details.append({
                        "id": paper_id,
                        "title": paper_info["title"],
                        "authors": paper_info["author"],
                        "conference": paper_info["conference_name"],
                        "year": int(paper_info["conference_year"]),
                        "coders": coders,
                        "initial_resolution_status": resolution_status,
                        "pdf_path": paper_info["path_pdf"].split("/")[-1]
                    })
            except (ValueError, KeyError) as e:
                app.logger.warning(f"Could not load details for paper {paper_id}: {str(e)}")
                continue
        
        return render_template("conflicts.html", papers=paper_details)
        
    except FileNotFoundError as e:
        app.logger.error(f"File not found: {str(e)}")
        return render_template("conflicts.html", 
                             papers=[], 
                             error=f"Required file not found: {str(e)}")
    except Exception as e:
        app.logger.error(f"Error loading conflict resolution interface: {str(e)}")
        return render_template("conflicts.html", 
                             papers=[], 
                             error=f"Failed to load conflict resolution interface: {str(e)}")


@app.route("/conflicts/paper/<paper_id>")
def paper_conflicts(paper_id):
    """Paper-specific conflict resolution page - load paper responses and identify conflicts."""
    try:
        # Validate paper_id
        if not paper_id or not paper_id.strip():
            return jsonify({"error": "Invalid paper ID"}), 400
        
        # Check if required files exist
        if not RESPONSES_DIR.exists() or not get_all_responses_paths():
            return jsonify({"error": "No response files found"}), 500
        
        if not PAPER_SELECTION_PATH.exists():
            return jsonify({"error": "Paper selection file not found"}), 500
        
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        conflict_analyzer = ConflictAnalyzer(CUSTOM_OPTIONS_PATH)
        initial_resolution_manager = InitialResolutionManager(INITIAL_RESOLUTIONS_DIR)
        
        # Load paper responses
        paper_responses = response_manager.load_paper_responses(paper_id)
        
        if not paper_responses:
            return render_template("paper_conflicts.html", 
                                 error=f"No responses found for paper {paper_id}")
        
        # Get available coders
        available_coders = conflict_analyzer.get_available_coders(paper_responses)
        
        if len(available_coders) < 2:
            return render_template("paper_conflicts.html", 
                                 error=f"Paper {paper_id} does not have multiple valid coder responses")
        
        # Check if paper has existing final responses (legacy paper)
        final_responses = response_manager._load_final_responses()
        has_existing_final = str(paper_id) in final_responses
        
        # If no existing final responses, check if both coders completed initial resolution
        if not has_existing_final:
            is_ready, completed_coders = initial_resolution_manager.is_paper_ready_for_final(
                paper_id, available_coders
            )
            
            if not is_ready:
                return render_template("paper_conflicts.html", 
                                     error=f"Paper {paper_id} is not ready for final resolution. "
                                           f"Both coders must complete initial resolution first. "
                                           f"Completed: {', '.join(completed_coders) if completed_coders else 'None'}")
            
            # Auto-populate based on initial resolutions
            response_manager.auto_populate_from_initial_resolutions(paper_id, INITIAL_RESOLUTIONS_DIR)
        
        # Get paper details
        try:
            papers_df = load_csv(PAPER_SELECTION_PATH, header=0)
            paper_row = papers_df.loc[papers_df["id"] == int(paper_id)]
            
            if paper_row.empty:
                return render_template("paper_conflicts.html", 
                                     error=f"Paper {paper_id} not found in paper selection file")
            
            paper_info = paper_row.iloc[0]
            paper_details = {
                "id": paper_id,
                "title": paper_info["title"],
                "authors": paper_info["author"],
                "conference": paper_info["conference_name"],
                "year": int(paper_info["conference_year"])
            }
            
        except (ValueError, KeyError) as e:
            app.logger.error(f"Error loading paper details for {paper_id}: {str(e)}")
            paper_details = {
                "id": paper_id,
                "title": f"Paper {paper_id}",
                "authors": "Unknown",
                "conference": "Unknown",
                "year": "Unknown"
            }
        
        return render_template("paper_conflicts.html", 
                             paper=paper_details, 
                             available_coders=available_coders)
        
    except FileNotFoundError as e:
        app.logger.error(f"File not found: {str(e)}")
        return jsonify({"error": f"Required file not found: {str(e)}"}), 500
    except Exception as e:
        app.logger.error(f"Error loading paper conflicts for {paper_id}: {str(e)}")
        return jsonify({"error": f"Failed to load paper conflicts: {str(e)}"}), 500


@app.route("/api/conflicts/<paper_id>")
def get_conflicts_data(paper_id):
    """Return JSON with conflict analysis and coder responses."""
    try:
        responses_signature = _directory_signature(RESPONSES_DIR, "responses_*.json")
        if not responses_signature:
            return jsonify({"error": "No responses found for this paper"}), 404

        cached_result, status_code = _get_conflicts_data_cached(
            paper_id,
            responses_signature,
            _path_signature(FINAL_RESPONSES_PATH) if FINAL_RESPONSES_PATH.exists() else (str(FINAL_RESPONSES_PATH), 0, 0),
            _directory_signature(INITIAL_RESOLUTIONS_DIR, "resolved_*.json"),
            _path_signature(SCHEMA_PATH),
            _path_signature(CUSTOM_OPTIONS_PATH),
        )

        return jsonify(copy.deepcopy(cached_result)), status_code
        
    except Exception as e:
        return jsonify({"error": f"Failed to get conflict data: {str(e)}"}), 500


@app.route("/api/question/<question_id>")
def get_question_metadata(question_id):
    """Return question text, options, and type information."""
    try:
        question_loader = QuestionLoader(SCHEMA_PATH, CUSTOM_OPTIONS_PATH)
        metadata = question_loader.get_question_metadata(question_id)
        
        if not metadata:
            return jsonify({"error": "Question not found"}), 404
        
        return jsonify(metadata)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get question metadata: {str(e)}"}), 500


@app.route("/api/conflicts/<paper_id>/question/<question_id>/with-comments")
def get_question_with_comments(paper_id, question_id):
    """Return question data including associated comment fields."""
    try:
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        conflict_analyzer = ConflictAnalyzer(CUSTOM_OPTIONS_PATH)
        
        # Load paper responses
        paper_responses = response_manager.load_paper_responses(paper_id)
        
        if not paper_responses:
            return jsonify({"error": "No responses found for this paper"}), 404
        
        # Get question with comments
        question_data = conflict_analyzer.get_question_with_comments(question_id, paper_responses)
        
        return jsonify(question_data)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get question with comments: {str(e)}"}), 500


@app.route("/api/conflicts/<paper_id>/<question_id>", methods=["PUT", "DELETE"])
def update_or_delete_final_response(paper_id, question_id):
    """Accept PUT requests to update final responses or DELETE requests to remove them."""
    try:
        # Validate paper_id
        if not paper_id or not paper_id.strip():
            return jsonify({"error": "Invalid paper ID"}), 400
        
        # Validate question_id
        if not question_id or not question_id.strip():
            return jsonify({"error": "Invalid question ID"}), 400
        
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        
        if request.method == "DELETE":
            # Delete the final response entry
            success = response_manager.delete_final_response(paper_id, question_id)
            
            if not success:
                return jsonify({"error": "Failed to delete final response. Please check server logs."}), 500
            
            response_data = {"status": "success", "message": "Final response deleted successfully"}
            
            if question_id.endswith('-Comment'):
                # For comment fields, return additional info about the main question
                base_question_id = question_id.replace('-Comment', '')
                response_data["base_question_id"] = base_question_id
            
            return jsonify(response_data)
        
        else:  # PUT request
            # Parse request data
            data = request.get_json()
            
            if not data or 'value' not in data:
                return jsonify({"error": "Missing 'value' in request body"}), 400
            
            value = data['value']
            
            # Validate input against question constraints
            question_loader = QuestionLoader(SCHEMA_PATH, CUSTOM_OPTIONS_PATH)
            
            # Special handling for comment fields - they don't exist in the schema
            if question_id.endswith('-Comment'):
                # Comment fields are always text fields, no validation needed beyond basic checks
                if isinstance(value, str) and len(value) > 10000:
                    return jsonify({"error": "Comment is too long (maximum 10,000 characters)"}), 400
            else:
                # Regular question validation
                question_metadata = question_loader.get_question_metadata(question_id)
                
                if not question_metadata:
                    return jsonify({"error": f"Question '{question_id}' not found in schema"}), 404
                
                # Perform type-based validation
                question_type = question_metadata.get('type', '')
                validation_error = validate_question_value(value, question_type, question_metadata)
                
                if validation_error:
                    return jsonify({"error": validation_error}), 400
            
            # Check if paper exists
            paper_responses = response_manager.load_paper_responses(paper_id)
            
            if not paper_responses:
                return jsonify({"error": f"No responses found for paper '{paper_id}'"}), 404
            
            # Save the final response
            success = response_manager.save_final_response(paper_id, question_id, value)
            
            if not success:
                return jsonify({"error": "Failed to save final response. Please check server logs."}), 500
            
            # If this is a comment field, also check if we need to update the main question status
            response_data = {"status": "success", "message": "Final response updated successfully"}
            
            if question_id.endswith('-Comment'):
                # For comment fields, return additional info about the main question
                base_question_id = question_id.replace('-Comment', '')
                response_data["base_question_id"] = base_question_id
            
            return jsonify(response_data)
        
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in request body"}), 400
    except Exception as e:
        app.logger.error(f"Error updating/deleting final response for paper {paper_id}, question {question_id}: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


def validate_question_value(value, question_type, metadata):
    """
    Validate a question value against its type and constraints.
    
    Args:
        value: The value to validate
        question_type: Type of the question
        metadata: Question metadata including options
        
    Returns:
        Error message string if validation fails, None if valid
    """
    # Handle empty values - allow empty strings for most question types
    if value is None or value == '':
        if metadata.get('required', False):
            return "This question is required and cannot be empty"
        return None  # Empty values are generally acceptable
    
    # Type-specific validation
    if question_type == 'checkbox':
        # Handle string values that should be arrays
        if isinstance(value, str):
            if value.strip() == '':
                return None  # Empty string is acceptable for optional checkbox
            # Try to parse comma-separated values
            value = [item.strip() for item in value.split(',') if item.strip()]
        
        if not isinstance(value, list):
            return "Checkbox questions require array values"
        
        # Validate each item in the array
        if len(value) == 0 and metadata.get('required', False):
            return "At least one option must be selected"
        
        # Check if values are valid options (only if options are defined)
        valid_options = [opt.get('value', opt) if isinstance(opt, dict) else opt 
                        for opt in metadata.get('options', [])]
        if valid_options:
            for item in value:
                if item not in valid_options:
                    return f"Invalid option: '{item}'"
    
    elif question_type in ['radiogroup', 'dropdown']:
        if isinstance(value, list):
            if not len(value) == 1:
                return "Single-select questions have to have one value only"
            value = value[0]
        
        # Check if value is a valid option (only if options are defined)
        valid_options = [opt.get('value', opt) if isinstance(opt, dict) else opt 
                        for opt in metadata.get('options', [])]
        if valid_options and value and value not in valid_options:
            return f"Invalid option: '{value}'"
    
    elif question_type == 'text':
        if not isinstance(value, str):
            # Try to convert to string
            value = str(value)
        
        # Check length constraints if any
        max_length = metadata.get('maxLength')
        if max_length and len(value) > max_length:
            return f"Text exceeds maximum length of {max_length} characters"
    
    elif question_type == 'number':
        if isinstance(value, str) and value.strip() == '':
            return None  # Empty string is acceptable for optional number fields
            
        try:
            num_value = float(value) if isinstance(value, str) else value
            
            # Check min/max constraints
            min_value = metadata.get('min')
            max_value = metadata.get('max')
            
            if min_value is not None and num_value < min_value:
                return f"Value must be at least {min_value}"
            
            if max_value is not None and num_value > max_value:
                return f"Value must be at most {max_value}"
                
        except (ValueError, TypeError):
            return "Invalid number format"
    
    elif question_type == 'boolean':
        if isinstance(value, str):
            if value.lower() in ['true', '1', 'yes']:
                return None
            elif value.lower() in ['false', '0', 'no', '']:
                return None
            else:
                return "Boolean questions require true/false values"
        elif not isinstance(value, bool):
            return "Boolean questions require true/false values"
    
    return None


# Initial Resolution Routes

@app.route("/initial-conflicts/<paper_id>")
def initial_resolve_conflicts(paper_id):
    """Initial resolution page for a specific paper."""
    # Get coder name from query parameter
    coder_name = request.args.get('coder')
    
    if not coder_name:
        return render_template("initial_resolution.html", 
                             error="Coder name is required. Please specify ?coder=<name> in the URL.")
    
    try:
        # Validate paper_id
        if not paper_id or not paper_id.strip():
            return jsonify({"error": "Invalid paper ID"}), 400
        
        # Check if required files exist
        if not RESPONSES_DIR.exists() or not get_all_responses_paths():
            return jsonify({"error": "No response files found"}), 500
        
        if not PAPER_SELECTION_PATH.exists():
            return jsonify({"error": "Paper selection file not found"}), 500
        
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        conflict_analyzer = ConflictAnalyzer(CUSTOM_OPTIONS_PATH)
        
        # Load paper responses
        paper_responses = response_manager.load_paper_responses(paper_id)
        
        if not paper_responses:
            return render_template("initial_resolution.html", 
                                 error=f"No responses found for paper {paper_id}")
        
        # Get available coders
        available_coders = conflict_analyzer.get_available_coders(paper_responses)
        
        if len(available_coders) < 2:
            return render_template("initial_resolution.html", 
                                 error=f"Paper {paper_id} does not have multiple valid coder responses")
        
        # Get paper details
        try:
            papers_df = load_csv(PAPER_SELECTION_PATH, header=0)
            paper_row = papers_df.loc[papers_df["id"] == int(paper_id)]
            
            if paper_row.empty:
                return render_template("initial_resolution.html", 
                                     error=f"Paper {paper_id} not found in paper selection file")
            
            paper_info = paper_row.iloc[0]
            paper_details = {
                "id": paper_id,
                "title": paper_info["title"],
                "authors": paper_info["author"],
                "conference": paper_info["conference_name"],
                "year": int(paper_info["conference_year"])
            }
            
        except (ValueError, KeyError) as e:
            app.logger.error(f"Error loading paper details for {paper_id}: {str(e)}")
            paper_details = {
                "id": paper_id,
                "title": f"Paper {paper_id}",
                "authors": "Unknown",
                "conference": "Unknown",
                "year": "Unknown"
            }
        
        # Load schema for button availability logic
        schema = load_json(SCHEMA_PATH)
        
        return render_template("initial_resolution.html", 
                             paper=paper_details, 
                             available_coders=available_coders,
                             coder_name=coder_name,
                             schema=schema)
        
    except FileNotFoundError as e:
        app.logger.error(f"File not found: {str(e)}")
        return jsonify({"error": f"Required file not found: {str(e)}"}), 500
    except Exception as e:
        app.logger.error(f"Error loading initial resolution for {paper_id}: {str(e)}")
        return jsonify({"error": f"Failed to load initial resolution: {str(e)}"}), 500


@app.route("/api/initial-conflicts/<paper_id>")
def get_initial_conflicts_data(paper_id):
    """Return JSON with conflict analysis and initial resolutions."""
    coder_name = request.args.get('coder')
    
    if not coder_name:
        return jsonify({"error": "Coder name is required"}), 400
    
    try:
        responses_signature = _directory_signature(RESPONSES_DIR, "responses_*.json")
        if not responses_signature:
            return jsonify({"error": "No responses found for this paper"}), 404

        cached_result, status_code = _get_initial_conflicts_data_cached(
            paper_id,
            coder_name,
            responses_signature,
            _directory_signature(INITIAL_RESOLUTIONS_DIR, "resolved_*.json"),
            _path_signature(SCHEMA_PATH),
            _path_signature(CUSTOM_OPTIONS_PATH),
        )

        return jsonify(copy.deepcopy(cached_result)), status_code
        
    except Exception as e:
        return jsonify({"error": f"Failed to get initial conflict data: {str(e)}"}), 500


@app.route("/api/initial-resolution/<paper_id>/<question_id>", methods=['PUT', 'GET'])
def handle_initial_resolution(paper_id, question_id):
    """Save or retrieve initial resolution decision."""
    
    if request.method == 'GET':
        # Get initial resolution
        coder_name = request.args.get('coder')
        
        if not coder_name:
            return jsonify({"error": "Coder name is required"}), 400
        
        try:
            initial_resolution_manager = InitialResolutionManager(INITIAL_RESOLUTIONS_DIR)
            resolutions = initial_resolution_manager.get_resolutions(paper_id, coder_name)
            
            resolution_data = resolutions.get("resolutions", {}).get(question_id, {})
            
            return jsonify({
                "paper_id": paper_id,
                "question_id": question_id,
                "coder_name": coder_name,
                "decision": resolution_data.get("decision", ""),
                "timestamp": resolution_data.get("timestamp", "")
            })
            
        except Exception as e:
            return jsonify({"error": f"Failed to get initial resolution: {str(e)}"}), 500
    
    else:  # PUT request
        # Save initial resolution
        data = request.get_json()
        
        if not data or 'decision' not in data or 'coder_name' not in data:
            return jsonify({"error": "Missing 'decision' or 'coder_name' in request body"}), 400
        
        decision = data['decision']
        coder_name = data['coder_name']
        
        # Get valid coder names for this paper
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        paper_responses = response_manager.load_paper_responses(paper_id)
        
        if not paper_responses:
            return jsonify({"error": "No responses found for this paper"}), 404
        
        conflict_analyzer = ConflictAnalyzer(CUSTOM_OPTIONS_PATH)
        coder_data = conflict_analyzer.get_coder_responses(paper_responses)
        valid_coder_names = list(coder_data.keys())
        
        # Validate decision - can be a coder name, Union, or Discuss
        valid_decisions = valid_coder_names + ['Union', 'Discuss']
        if decision not in valid_decisions:
            return jsonify({"error": f"Invalid decision. Must be one of: {', '.join(valid_decisions)}"}), 400
        
        # Don't allow initial resolution for comment fields
        if question_id.endswith('-Comment'):
            return jsonify({"error": "Comment fields cannot be resolved in initial resolution"}), 400
        
        try:
            initial_resolution_manager = InitialResolutionManager(INITIAL_RESOLUTIONS_DIR)
            success = initial_resolution_manager.save_resolution(paper_id, coder_name, question_id, decision)
            
            if not success:
                return jsonify({"error": "Failed to save initial resolution"}), 500
            
            return jsonify({
                "status": "success",
                "message": "Initial resolution saved successfully",
                "paper_id": paper_id,
                "question_id": question_id,
                "coder_name": coder_name,
                "decision": decision
            })
            
        except Exception as e:
            app.logger.error(f"Error saving initial resolution: {str(e)}")
            return jsonify({"error": f"Failed to save initial resolution: {str(e)}"}), 500


@app.route("/api/initial-resolution/<paper_id>/status")
def get_initial_resolution_status(paper_id):
    """Get the initial resolution status for a paper."""
    try:
        response_manager = ResponseManager(RESPONSES_DIR, FINAL_RESPONSES_PATH, SCHEMA_PATH)
        initial_resolution_manager = InitialResolutionManager(response_manager, INITIAL_RESOLUTIONS_DIR, CUSTOM_OPTIONS_PATH)
        status = initial_resolution_manager.get_resolution_status(paper_id)
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get resolution status: {str(e)}"}), 500



if __name__ == "__main__":
    app.run(debug=True, port=5001)
