%% ============================================================================
%  PROVENANCE / DATA SOURCE
%  ---------------------------------------------------------------------------
%  This is the ORIGINAL, verified derivation script that produces the analysed
%  event-sequence datasets shipped in ../ (worldcup_goals.csv, worldcup_nongoals.csv,
%  worldcup_defensive_recovery.csv). It reads the openly released PFF FC 2022 FIFA
%  World Cup event JSONs and writes the shot-ending possession sequences in both a
%  flat per-event table and THEME .obs format.
%
%  Input  : a folder of PFF World Cup event JSON files (one per match). Obtain the
%           dataset from PFF FC's open research release (see ../README.md and the
%           paper's data-availability statement for the access URL).
%  Output : Temporal_Sequences.csv, Temporal_SequenceSummary.csv, and the THEME
%           .obs files. The shipped worldcup_*.csv are these sequences in the
%           library's canonical flat format (observation, event, start[ms],
%           obs_start, obs_end); see ../README.md.
%
%  Runtime: MATLAB (developed on R2022a). Set the two CONFIG paths below before
%           running. This script is provided as the documented, already-verified
%           derivation of record; a Python port may follow.
%
%  Cite the source data as: PFF Sports (2022), 2022 FIFA World Cup event data.
%% ============================================================================

%% Temporal_Step1_ExtractSequences.m
%
% Extracts shot-ending possession sequences from all 64 PFF 2022 World Cup
% event JSONs and produces two output files for downstream analysis:
%
%   Temporal_Sequences.csv       — one row per EVENT within a sequence
%   Temporal_SequenceSummary.csv — one row per SEQUENCE (i.e. per shot)
%
% === Sequence definition ===
%
%   Option B (continuous possession) with a 60-second lookback cap.
%   For each qualifying shot, the script walks backwards through the event
%   stream and collects all consecutive events belonging to the SAME team,
%   stopping when:
%     (a) a team possession change is detected (gameEvents.teamId changes
%         OR an IT event is found for the opposing team), or
%     (b) the elapsed time since the candidate event exceeds 60 seconds, or
%     (c) a game stoppage is detected (gap > 5s between consecutive events
%         of any type, used as a soft break marker — see note below).
%
%   NOTE on stoppage detection: within a continuous possession the event
%   stream continues at the ~1.4s median resolution. A gap > 5s between
%   consecutive events strongly implies an out-of-play stoppage. We treat
%   this as a possession boundary. If the gap occurs WITHIN what looks like
%   the same team's possession, the sequence is truncated at that point.
%
% === Shot eligibility (same exclusions as interpersonal paper) ===
%
%   Applied in order:
%     1. Missing ball coordinates
%     2. Own-half shot (ball_x_norm < 0 after attack direction normalisation)
%     3. Ball beyond goal line (ball_x_norm > 52.5)
%     4. Penalty kick (setpieceType = 'P')
%     5. Shot distance >= 55 m
%
%   Attack direction: inferred from median ball_x of shots per (team, period).
%   Do NOT use homeTeamStartLeft metadata (inconsistent sign convention).
%
% === Event coding — full descriptive text ===
%
%   Applied inline during extraction. Each event gets a plain-English code
%   for clarity in manuscript reporting and THEME pattern output.
%   Format: EventType_Outcome_PressureContext
%
%     Pass:      Pass_Complete_NoPressure | Pass_Complete_Pressure |
%                Pass_Complete_Anticipation | Pass_Complete_LooseBall |
%                Pass_Incomplete_* | Pass_ShotAssist_* | Pass_Offside
%
%     Cross:     Cross_Complete_* | Cross_Incomplete_* | Cross_ShotAssist_*
%
%     Challenge: Challenge_NoPressure | Challenge_Pressure |
%                Challenge_Anticipation | Challenge_LooseBall
%                (no win/loss field in raw data)
%
%     Shot:      Shot_Goal_* | Shot_Saved_* | Shot_Blocked_* | Shot_OffTarget_*
%                Pressure suffixes as above
%
%     Other:     Clearance_* | Touch_* | BallCarry_* | Recovery_*
%                Interception  (no pressure sub-qualifier)
%
%   The descriptive code is stored in the 'event_code_L2' column.
%   The raw PFF type code is preserved in 'event_type'.
%
% === THEME-format output ===
%
%   Also writes:
%     Temporal_THEME_Goals.obs      — sequences for GOAL shots
%     Temporal_THEME_NonGoals.obs   — sequences for all non-goal shots
%     Temporal_THEME_Saved.obs      — sequences for DEF_RECOVERY shots only
%
%   Format: [sequence_id]  [time_from_seq_start_s]  [event_code_L2]
%   (tab-separated, no header, one event per line)
%
% === Output columns ===
%
%   Temporal_Sequences.csv:
%     sequence_id, game_id, shot_outcome, shot_index,
%     event_index_in_seq, event_type, event_code_L2,
%     abs_time_s, rel_time_s (from seq start), pressure_type,
%     team_id, period
%
%   Temporal_SequenceSummary.csv:
%     sequence_id, game_id, shot_outcome, shot_index,
%     period, game_clock_s, t_shot_s,
%     team_id, player_id, jersey_num, pressure_type_at_shot,
%     ball_x_norm, ball_y_norm, shot_dist_norm_m,
%     sequence_duration_s, n_events, n_passes, n_challenges, n_crosses,
%     n_under_pressure, pass_completion_rate,
%     final_event_type (event immediately before shot),
%     sequence_type (COUNTER = duration<10s OR n_events<=3 | BUILD_UP otherwise)
%
% Andy Callaway - Bournemouth University
% v1 — April 2026

clear; clc;

%% ===== CONFIGURATION =====================================================

CONFIG.event_folder  = 'PFF_EventData';   % <-- set to your folder of PFF World Cup event JSONs
CONFIG.output_folder = 'Temporal_out';    % <-- set to your desired output folder

% Pitch constants (metres)
CONFIG.pitch_half_x   = 52.5;
CONFIG.pitch_half_y   = 34.0;
CONFIG.goal_y_post    = 3.66;
CONFIG.goal_x         = 52.5;

% Sequence extraction parameters
CONFIG.max_seq_duration_s  = 60.0;   % lookback cap (Option B)
CONFIG.stoppage_gap_s      = 5.0;    % inter-event gap that signals stoppage
CONFIG.stop_at_prev_shot   = true;   % true = each shot starts a fresh sequence
                                     %   (rebound shot does not inherit blocked attempt)
                                     % false = walk back through preceding SH events
                                     %   (blocked-then-rebound treated as one sequence)
CONFIG.max_shot_dist_m     = 55.0;   % exclusion: shots >= this distance

% Sequence type threshold
CONFIG.counter_attack_dur_s    = 10.0;  % sequences < this OR <= 3 events -> COUNTER
CONFIG.counter_attack_n_events = 3;

%% ===== SETUP =============================================================

if ~exist(CONFIG.output_folder, 'dir'), mkdir(CONFIG.output_folder); end

json_files = dir(fullfile(CONFIG.event_folder, '*.json'));
if isempty(json_files)
    error('No JSON files found in: %s', CONFIG.event_folder);
end
fprintf('Found %d event JSON files.\n\n', numel(json_files));

%% ===== STORAGE ===========================================================

all_seq_events  = {};   % cell array of rows for Temporal_Sequences.csv
all_seq_summary = {};   % cell array of rows for Temporal_SequenceSummary.csv

% THEME: collect per-sequence event lists, keyed by seq_id
% Each entry: {seq_id, outcome, {[t_ms, code], ...}}
theme_sequences = {};   % all sequences in insertion order

n_total_shots     = 0;
n_excluded        = 0;
n_sequences       = 0;

%% ===== MAIN LOOP =========================================================

for fi = 1:numel(json_files)

    fname   = json_files(fi).name;
    fpath   = fullfile(CONFIG.event_folder, fname);
    game_id = strrep(fname, '.json', '');

    fprintf('[%d/%d] Game %s ... ', fi, numel(json_files), game_id);

    %% Load JSON
    fid = fopen(fpath, 'r');
    raw = fread(fid, '*char')';
    fclose(fid);
    try
        events = jsondecode(raw);
    catch ME
        fprintf('PARSE ERROR: %s\n', ME.message);
        continue;
    end

    if isstruct(events)
        n_ev = numel(events);
        get_ev = @(i) events(i);
    elseif iscell(events)
        n_ev = numel(events);
        get_ev = @(i) events{i};
    else
        fprintf('Unexpected structure — skipping.\n');
        continue;
    end

    %% Pre-pass 1: build attack direction map (median shot ball_x per team/period)
    atk_dir_map    = containers.Map('KeyType','char','ValueType','logical');
    team_period_x  = containers.Map('KeyType','char','ValueType','any');

    for ei = 1:n_ev
        ev = get_ev(ei);
        pe = ev.possessionEvents;
        if ~isstruct(pe) || ~isfield(pe,'possessionEventType'), continue; end
        if ~strcmp(pe.possessionEventType,'SH'), continue; end
        ge  = ev.gameEvents;
        tid = safe_str(ge,'teamId');
        per = safe_num(ge,'period');
        if isnan(per) || isempty(tid), continue; end
        [bx,~] = get_ball_pos(ev);
        if isnan(bx), continue; end
        key = sprintf('%s_%d', tid, per);
        if isKey(team_period_x, key)
            team_period_x(key) = [team_period_x(key), bx];
        else
            team_period_x(key) = bx;
        end
    end
    for k = keys(team_period_x)
        atk_dir_map(k{1}) = median(team_period_x(k{1})) > 0;
    end

    %% Pre-pass 2: build flat event list for this game
    %  We need to walk backwards from a shot, so build an index first.
    %  Store: abs_time, team_id, event_type, possessionEvents struct, gameEvents struct

    ev_times    = NaN(n_ev, 1);
    ev_types    = cell(n_ev, 1);
    ev_team_ids = cell(n_ev, 1);
    ev_periods  = NaN(n_ev, 1);

    for ei = 1:n_ev
        ev = get_ev(ei);
        ev_times(ei)    = safe_num(ev, 'startTime');
        ge = ev.gameEvents;
        ev_team_ids{ei} = safe_str(ge, 'teamId');
        ev_periods(ei)  = safe_num(ge, 'period');
        pe = ev.possessionEvents;
        if isstruct(pe) && isfield(pe,'possessionEventType')
            ev_types{ei} = char(pe.possessionEventType);
        else
            ge_type = safe_str(ge, 'gameEventType');
            if ~isempty(ge_type)
                ev_types{ei} = char(ge_type);
            else
                ev_types{ei} = 'UNK';
            end
        end
    end

    %% Shot loop
    n_shots_this = 0;
    n_goals_this = 0;

    for ei = 1:n_ev

        ev = get_ev(ei);
        pe = ev.possessionEvents;
        if ~isstruct(pe) || ~isfield(pe,'possessionEventType'), continue; end
        if ~strcmp(pe.possessionEventType,'SH'), continue; end

        ge = ev.gameEvents;

        n_total_shots = n_total_shots + 1;

        %% Shot identifiers
        t_shot     = safe_num(ev, 'startTime');
        period     = safe_num(ge, 'period');
        game_clock = safe_num(ge, 'startGameClock');
        team_id    = safe_str(ge, 'teamId');
        player_id  = safe_str(ge, 'playerId');
        jersey_num = safe_num(ge, 'jerseyNum');
        is_penalty = strcmp(safe_str(ge,'setpieceType'), 'P');
        pressure   = safe_str(pe, 'pressureType');

        %% Ball position and attack direction
        [ball_x_raw, ball_y_raw] = get_ball_pos(ev);
        atk_key = sprintf('%s_%d', team_id, period);
        if isKey(atk_dir_map, atk_key)
            atk_pos = atk_dir_map(atk_key);
        else
            atk_pos = true;   % fallback (rarely triggered)
        end

        % Normalise to attacking-right frame
        if atk_pos
            ball_x_norm = ball_x_raw;
            ball_y_norm = ball_y_raw;
        else
            ball_x_norm = -ball_x_raw;
            ball_y_norm = -ball_y_raw;
        end

        %% Shot distance
        shot_dist_m = sqrt((CONFIG.goal_x - ball_x_norm)^2 + ball_y_norm^2);

        %% Outcome
        sot = safe_str(pe, 'shotOutcomeType');
        switch sot
            case 'G',        outcome = 'GOAL';
            case {'S','B'},  outcome = 'DEF_RECOVERY';
            case 'O',        outcome = 'OFF_TARGET';
            otherwise,       outcome = 'UNKNOWN';
        end

        %% Apply exclusions
        excl_reason = '';
        if isnan(ball_x_raw) || isnan(ball_y_raw)
            excl_reason = 'MISSING_BALL';
        elseif ball_x_norm < 0
            excl_reason = 'OWN_HALF';
        elseif ball_x_norm > CONFIG.goal_x
            excl_reason = 'BEYOND_GOALLINE';
        elseif is_penalty
            excl_reason = 'PENALTY';
        elseif ~isnan(shot_dist_m) && shot_dist_m >= CONFIG.max_shot_dist_m
            excl_reason = 'DISTANCE_GTE55M';
        end

        if ~isempty(excl_reason)
            n_excluded = n_excluded + 1;
            continue;
        end

        n_shots_this = n_shots_this + 1;
        if strcmp(outcome, 'GOAL'), n_goals_this = n_goals_this + 1; end

        n_sequences = n_sequences + 1;
        shot_index  = n_sequences;
        seq_id      = sprintf('seq_%s_%04d', game_id, shot_index);

        %% Walk backwards to extract possession sequence
        %
        % Collect event indices (in forward order) that belong to this
        % shot-ending possession. Rules:
        %   - Same team as shooter (team_id match)
        %   - Same period
        %   - No gap > CONFIG.stoppage_gap_s between consecutive events
        %   - Time within CONFIG.max_seq_duration_s of the shot
        %   - Stop at any preceding IT event belonging to the OPPOSING team
        %     (that marks the start of this team's possession) OR at any
        %     IT event that belongs to the shooting team (opponent's last IT)
        %
        % We also include the shot event itself as the LAST event.

        seq_indices = [];   % will hold event indices in REVERSE order first

        % Start from the shot event itself
        seq_indices(end+1) = ei; %#ok<AGROW>
        prev_time = t_shot;

        j = ei - 1;
        while j >= 1

            % Must be same period
            if ev_periods(j) ~= period, break; end

            % Gap check (stoppage detection)
            t_j = ev_times(j);
            if isnan(t_j), j = j - 1; continue; end
            gap = prev_time - t_j;
            if gap > CONFIG.stoppage_gap_s, break; end

            % Lookback cap
            if (t_shot - t_j) > CONFIG.max_seq_duration_s, break; end

            % Event type
            etype_j = ev_types{j};

            % Optional: stop when a preceding SH is encountered.
            % Keeps each shot as an independent sequence — rebound shots
            % do not inherit the blocked attempt that preceded them.
            if CONFIG.stop_at_prev_shot && strcmp(etype_j, 'SH')
                break;
            end

            % Check team ownership
            tid_j = ev_team_ids{j};

            % IT event rules:
            %   If IT belongs to opponent -> this marks end of opponent's
            %   possession and start of ours -> include the IT? No: the IT
            %   is the opponent's action. Stop HERE (don't include the IT).
            %   If IT belongs to same team -> unusual but include (recovery).
            if strcmp(etype_j, 'IT')
                if ~strcmp(tid_j, team_id)
                    % This IT is the opponent recovering the ball — means
                    % our possession started AFTER this event. Stop.
                    break;
                end
                % Same-team IT (e.g. winning a loose ball) — include it.
            end

            % If any event belongs to the opposing team (not IT) -> stop.
            % We allow empty team IDs to pass through (game/admin events).
            if ~isempty(tid_j) && ~strcmp(tid_j, team_id) && ~strcmp(etype_j,'IT')
                break;
            end

            % Game administrative events (OUT, END, SUB, etc.) that are
            % not possession events — treat as stoppage markers.
            if any(strcmp(etype_j, {'OUT','END','SUB','FIRSTKICKOFF','SECONDKICKOFF'}))
                break;
            end

            seq_indices(end+1) = j; %#ok<AGROW>
            prev_time = t_j;
            j = j - 1;
        end

        % Reverse to get chronological order
        seq_indices = fliplr(seq_indices);

        %% Level 2 coding for each event in the sequence
        seq_rows   = {};
        theme_rows = {};

        t_seq_start = ev_times(seq_indices(1));

        n_pa = 0; n_ch = 0; n_cr = 0; n_pressure = 0; n_simul_it = 0;
        n_pa_complete = 0; n_pa_total = 0;
        final_etype = '';

        for si = 1:numel(seq_indices)
            idx = seq_indices(si);
            ev_i = get_ev(idx);
            pe_i = ev_i.possessionEvents;
            ge_i = ev_i.gameEvents;

            etype    = ev_types{idx};
            abs_t    = ev_times(idx);
            rel_t    = abs_t - t_seq_start;
            press_i  = '';
            if isstruct(pe_i) && isfield(pe_i, 'pressureType')
                press_i = safe_str(pe_i, 'pressureType');
            end
            if isempty(press_i), press_i = 'N'; end   % default: no pressure

            %% Compute Level 2 code
            code_L2 = compute_L2_code(etype, pe_i, press_i);

            %% Accumulate sequence statistics
            if strcmp(etype, 'PA')
                n_pa = n_pa + 1;
                n_pa_total = n_pa_total + 1;
                po = '';
                if isstruct(pe_i) && isfield(pe_i,'passOutcomeType')
                    po = safe_str(pe_i,'passOutcomeType');
                end
                if strcmp(po,'C') || strcmp(po,'S')
                    n_pa_complete = n_pa_complete + 1;
                end
            elseif strcmp(etype,'CH'), n_ch = n_ch + 1;
            elseif strcmp(etype,'CR'), n_cr = n_cr + 1;
            end
            if any(strcmp(press_i, {'P','A'})), n_pressure = n_pressure + 1; end

            % Track final event before shot.
            % Skip IT events that share the shot timestamp (PFF simultaneous
            % IT+SH encoding — not a true preceding action).
            if si == numel(seq_indices) - 1
                t_shot_ev = ev_times(seq_indices(end));
                if strcmp(etype, 'IT') && abs(abs_t - t_shot_ev) < 0.001
                    n_simul_it = n_simul_it + 1;
                    if si >= 2
                        final_etype = char(ev_types{seq_indices(si-1)});
                    else
                        final_etype = 'IT_SIMUL';
                    end
                else
                    final_etype = etype;
                end
            end

            %% Accumulate row for Temporal_Sequences.csv
            row = {seq_id, game_id, outcome, shot_index, ...
                   si, etype, code_L2, ...
                   abs_t, rel_t, press_i, team_id, period};
            seq_rows{end+1} = row; %#ok<AGROW>

            %% Accumulate THEME event [t_ms, code]
            % Convert relative time (s) to milliseconds integer
            t_ms = max(2, round(rel_t * 1000) + 2);  % offset+2 so > start marker at 1
            theme_rows{end+1} = {t_ms, code_L2}; %#ok<AGROW>
        end

        %% Sequence-level summary
        seq_dur    = ev_times(seq_indices(end)) - t_seq_start;
        n_ev_seq   = numel(seq_indices);

        if n_pa_total > 0
            pass_comp = n_pa_complete / n_pa_total;
        else
            pass_comp = NaN;
        end

        if seq_dur < CONFIG.counter_attack_dur_s || n_ev_seq <= CONFIG.counter_attack_n_events
            seq_type = 'COUNTER';
        else
            seq_type = 'BUILD_UP';
        end

        if isempty(final_etype), final_etype = ''; end

        summary_row = {seq_id, game_id, outcome, shot_index, ...
                       sn(period), sn(game_clock), sn(t_shot), ...
                       team_id, player_id, sn(jersey_num), pressure, ...
                       sn(ball_x_norm), sn(ball_y_norm), sn(shot_dist_m), ...
                       sn(seq_dur), sn(n_ev_seq), sn(n_pa), sn(n_ch), sn(n_cr), ...
                       sn(n_pressure), pass_comp, ...
                       sn(n_simul_it), final_etype, seq_type};
        all_seq_summary{end+1} = summary_row; %#ok<AGROW>

        %% Append event rows
        for ri = 1:numel(seq_rows)
            all_seq_events{end+1} = seq_rows{ri}; %#ok<AGROW>
        end

        %% Store THEME sequence entry: {seq_id, outcome, events_cell}
        theme_sequences{end+1} = {seq_id, outcome, theme_rows}; %#ok<AGROW>

    end  % shot loop

    fprintf('%d shots, %d goals [post-exclusion; excl. penalties, own-half, >55m].\n', n_shots_this, n_goals_this);

end  % file loop

%% ===== ASSEMBLE AND SAVE: Temporal_Sequences.csv =========================

fprintf('\n--- Assembling event table (%d rows) ...\n', numel(all_seq_events));

if ~isempty(all_seq_events)

    seq_col_names = {'sequence_id','game_id','shot_outcome','shot_index', ...
                     'event_index_in_seq','event_type','event_code_L2', ...
                     'abs_time_s','rel_time_s','pressure_type', ...
                     'team_id','period'};

    first = all_seq_events{1};
    is_num = cellfun(@isnumeric, first);
    n_rows  = numel(all_seq_events);
    n_cols  = numel(seq_col_names);

    num_data = NaN(n_rows, sum(is_num));
    str_data = cell(n_rows, sum(~is_num));
    num_idx  = find(is_num);
    str_idx  = find(~is_num);

    for ri = 1:n_rows
        row = all_seq_events{ri};
        for k = 1:numel(num_idx)
            v = row{num_idx(k)};
            if isnumeric(v) && ~isempty(v), num_data(ri,k) = double(v(1)); end
        end
        for k = 1:numel(str_idx)
            v = row{str_idx(k)};
            if ischar(v)||isstring(v), str_data{ri,k} = char(v);
            else, str_data{ri,k} = ''; end
        end
    end

    T_seq = table();
    ni = 0; si = 0;
    for ci = 1:n_cols
        if is_num(ci)
            ni = ni + 1; T_seq.(seq_col_names{ci}) = num_data(:,ni);
        else
            si = si + 1; T_seq.(seq_col_names{ci}) = str_data(:,si);
        end
    end

    out1 = fullfile(CONFIG.output_folder, 'Temporal_Sequences.csv');
    writetable(T_seq, out1);
    fprintf('Saved: %s\n', out1);
end

%% ===== ASSEMBLE AND SAVE: Temporal_SequenceSummary.csv ===================

fprintf('Assembling summary table (%d rows) ...\n', numel(all_seq_summary));

if ~isempty(all_seq_summary)

    sum_col_names = {'sequence_id','game_id','shot_outcome','shot_index', ...
                     'period','game_clock_s','t_shot_s', ...
                     'team_id','player_id','jersey_num','pressure_type_at_shot', ...
                     'ball_x_norm','ball_y_norm','shot_dist_norm_m', ...
                     'sequence_duration_s','n_events','n_passes','n_challenges','n_crosses', ...
                     'n_under_pressure','pass_completion_rate', ...
                     'n_simul_it_events','final_event_type','sequence_type'};

    first = all_seq_summary{1};
    is_num = cellfun(@isnumeric, first);
    n_rows = numel(all_seq_summary);
    n_cols = numel(sum_col_names);

    num_data = NaN(n_rows, sum(is_num));
    str_data = cell(n_rows, sum(~is_num));
    num_idx  = find(is_num);
    str_idx  = find(~is_num);

    for ri = 1:n_rows
        row = all_seq_summary{ri};
        for k = 1:numel(num_idx)
            v = row{num_idx(k)};
            if isnumeric(v) && ~isempty(v), num_data(ri,k) = double(v(1)); end
        end
        for k = 1:numel(str_idx)
            v = row{str_idx(k)};
            if ischar(v)||isstring(v), str_data{ri,k} = char(v);
            else, str_data{ri,k} = ''; end
        end
    end

    T_sum = table();
    ni = 0; si = 0;
    for ci = 1:n_cols
        if is_num(ci)
            ni = ni + 1; T_sum.(sum_col_names{ci}) = num_data(:,ni);
        else
            si = si + 1; T_sum.(sum_col_names{ci}) = str_data(:,si);
        end
    end

    out2 = fullfile(CONFIG.output_folder, 'Temporal_SequenceSummary.csv');
    writetable(T_sum, out2);
    fprintf('Saved: %s\n', out2);
end

%% ===== SAVE THEME FOLDERS ================================================
%
% Writes one .txt file per sequence plus a vvt.vvt category table into
% three subfolders: THEME_Goals, THEME_NonGoals, THEME_Saved.
% Each .txt file is a valid THEME raw data file:
%   Line 1 : time {tab} event   (header)
%   Line 2 : 1 {tab} :          (start-of-observation marker)
%   Lines  : t_ms {tab} code    (events, times in milliseconds, integers)
%   Last   : t_end {tab} &      (end-of-observation marker)
% Times are relative to sequence start, multiplied by 1000 and rounded.

theme_goal_seqs    = theme_sequences(cellfun(@(s) strcmp(s{2},'GOAL'),         theme_sequences));
theme_nongoal_seqs = theme_sequences(cellfun(@(s) ~strcmp(s{2},'GOAL'),        theme_sequences));
theme_saved_seqs   = theme_sequences(cellfun(@(s) strcmp(s{2},'DEF_RECOVERY'), theme_sequences));

write_theme_folder(theme_goal_seqs,    fullfile(CONFIG.output_folder, 'THEME_Goals'),    'g');
write_theme_folder(theme_nongoal_seqs, fullfile(CONFIG.output_folder, 'THEME_NonGoals'), 'n');
write_theme_folder(theme_saved_seqs,   fullfile(CONFIG.output_folder, 'THEME_Saved'),    's');

%% ===== PIPELINE SUMMARY ==================================================

fprintf('\n========================================\n');
fprintf('PIPELINE SUMMARY\n');
fprintf('========================================\n');
fprintf('Total SH events found    : %d  (all shots, pre-exclusion)\n', n_total_shots);
fprintf('Excluded                 : %d  (missing ball / own-half / beyond line / penalty / >=55m)\n', n_excluded);
fprintf('Sequences extracted      : %d  (post-exclusion — should match interpersonal paper N)\n', n_sequences);
fprintf('THEME sequences (goals)      : %d\n', numel(theme_goal_seqs));
fprintf('THEME sequences (non-goals)  : %d\n', numel(theme_nongoal_seqs));
fprintf('THEME sequences (saved only) : %d\n', numel(theme_saved_seqs));

if ~isempty(all_seq_summary)
    outcomes = cellfun(@(r) r{3}, all_seq_summary, 'UniformOutput', false);
    for oc = {'GOAL','DEF_RECOVERY','OFF_TARGET','UNKNOWN'}
        n = sum(strcmp(outcomes, oc{1}));
        fprintf('  %-14s : %4d  (%.1f%%)\n', oc{1}, n, 100*n/n_sequences);
    end

    % Summary row column positions (1-indexed):
    %  1=seq_id  2=game_id  3=outcome  4=shot_idx  5=period  6=game_clock  7=t_shot
    %  8=team_id  9=player_id  10=jersey  11=pressure  12=ball_x  13=ball_y  14=dist
    %  15=seq_dur  16=n_events  17=n_passes  18=n_ch  19=n_cr  20=n_pressure
    %  21=pass_comp  22=n_simul_it  23=final_etype  24=seq_type
    durs     = cellfun(@(r) r{15}, all_seq_summary);
    nevents  = cellfun(@(r) r{16}, all_seq_summary);
    seqtypes = cellfun(@(r) r{24}, all_seq_summary, 'UniformOutput', false);
    fprintf('\nSequence duration (s)    : M=%.1f  Mdn=%.1f  SD=%.1f  [%.1f – %.1f]\n', ...
        mean(durs,'omitnan'), median(durs,'omitnan'), std(durs,'omitnan'), ...
        min(durs), max(durs));
    fprintf('Sequence length (events) : M=%.1f  Mdn=%.1f  SD=%.1f  [%d – %d]\n', ...
        mean(nevents,'omitnan'), median(nevents,'omitnan'), std(nevents,'omitnan'), ...
        min(nevents), max(nevents));
    n_counter  = sum(strcmp(seqtypes,'COUNTER'));
    n_buildup  = sum(strcmp(seqtypes,'BUILD_UP'));
    fprintf('Counter-attack sequences : %d (%.1f%%)\n', n_counter, 100*n_counter/n_sequences);
    fprintf('Build-up sequences       : %d (%.1f%%)\n', n_buildup, 100*n_buildup/n_sequences);
end

fprintf('\nDone.\n');


%% =========================================================================
%% LOCAL FUNCTIONS
%% =========================================================================

function code = compute_L2_code(etype, pe, press_code)
% Returns a full-text descriptive event code for a single event.
% Uses plain English names rather than abbreviations for clarity
% in manuscript reporting and THEME output files.
%
% pe:         possessionEvents struct (may be empty for game admin events)
% press_code: pressure type ('N'=NoPressure 'P'=Pressure
%                             'A'=Anticipation 'L'=LooseBall)

    etype      = char(etype);
    press_code = char(press_code);
    if isempty(press_code), press_code = 'N'; end

    % Map single-letter pressure code to full descriptive text
    switch press_code
        case 'N', press_str = 'NoPressure';
        case 'P', press_str = 'Pressure';
        case 'A', press_str = 'Anticipation';
        case 'L', press_str = 'LooseBall';
        otherwise, press_str = 'NoPressure';
    end

    switch etype
        case 'PA'
            po = '';
            if isstruct(pe) && isfield(pe,'passOutcomeType')
                po = safe_str(pe,'passOutcomeType');
            end
            switch po
                case 'C',  out_str = 'Complete';
                case 'D',  out_str = 'Incomplete';
                case 'S',  out_str = 'ShotAssist';
                case 'B',  out_str = 'Incomplete';
                case 'O',  code = 'Pass_Offside'; return;
                otherwise, out_str = 'Incomplete';
            end
            code = sprintf('Pass_%s_%s', out_str, press_str);

        case 'CR'
            po = '';
            if isstruct(pe) && isfield(pe,'passOutcomeType')
                po = safe_str(pe,'passOutcomeType');
            end
            switch po
                case 'C',  out_str = 'Complete';
                case 'D',  out_str = 'Incomplete';
                case 'S',  out_str = 'ShotAssist';
                case 'B',  out_str = 'Incomplete';
                otherwise, out_str = 'Incomplete';
            end
            code = sprintf('Cross_%s_%s', out_str, press_str);

        case 'CH'
            code = sprintf('Challenge_%s', press_str);

        case 'SH'
            sot = '';
            if isstruct(pe) && isfield(pe,'shotOutcomeType')
                sot = safe_str(pe,'shotOutcomeType');
            end
            switch sot
                case 'G',  out_str = 'Goal';
                case 'S',  out_str = 'Saved';
                case 'B',  out_str = 'Blocked';
                case 'O',  out_str = 'OffTarget';
                otherwise, out_str = 'OffTarget';
            end
            code = sprintf('Shot_%s_%s', out_str, press_str);

        case 'CL'
            code = sprintf('Clearance_%s', press_str);

        case 'TC'
            code = sprintf('Touch_%s', press_str);

        case 'BC'
            code = sprintf('BallCarry_%s', press_str);

        case 'RE'
            code = sprintf('Recovery_%s', press_str);

        case 'IT'
            code = 'Interception';

        otherwise
            code = etype;
    end
end

% --------------------------

function write_theme_folder(seq_list, folder_path, prefix)
% Write one THEME-format .txt file per sequence into folder_path.
% Also writes vvt.vvt category table listing all event codes.
%
% seq_list : cell array of {seq_id, outcome, events}
%            events = cell array of {t_ms (int), code (char)}
% prefix   : single letter prefix for filenames ('g','n','s')

    if isempty(seq_list)
        fprintf('No sequences to write for: %s\n', folder_path);
        return;
    end

    if ~exist(folder_path, 'dir'), mkdir(folder_path); end

    all_codes = {};
    n_written = 0;

    for si = 1:numel(seq_list)
        seq_id  = seq_list{si}{1};
        events  = seq_list{si}{3};   % cell array of {t_ms, code}

        % Build filename: prefix + seq_id stripped of non-alphanumeric
        fname_base = regexprep(seq_id, '[^a-zA-Z0-9]', '');
        fname = fullfile(folder_path, [prefix, fname_base, '.txt']);

        fid = fopen(fname, 'w');
        if fid < 0
            fprintf('ERROR: Cannot open %s\n', fname);
            continue;
        end

        % Header
        fprintf(fid, 'time\tevent\n');
        % Start-of-observation marker (time=1, before first event at t>=2)
        fprintf(fid, '1\t:\n');

        % Events
        t_last = 2;
        for ei = 1:numel(events)
            t_ms   = events{ei}{1};
            code   = events{ei}{2};
            fprintf(fid, '%d\t%s\n', t_ms, code);
            all_codes{end+1} = lower(code); %#ok<AGROW>
            if t_ms > t_last, t_last = t_ms; end
        end

        % End-of-observation marker (1 ms after last event)
        fprintf(fid, '%d\t&\n', t_last + 1);
        fclose(fid);
        n_written = n_written + 1;
    end

    % Write vvt.vvt category table
    % Format: class name (no indent), items indented with one space
    % THEME converts everything to lowercase automatically
    unique_codes = unique(all_codes);
    vvt_path = fullfile(folder_path, 'vvt.vvt');
    fid = fopen(vvt_path, 'w');
    if fid >= 0
        fprintf(fid, 'action\n');
        for ci = 1:numel(unique_codes)
            fprintf(fid, ' %s\n', unique_codes{ci});
        end
        fprintf(fid, '\n');   %% trailing newline required by THEME
        fclose(fid);
    end

    fprintf('Saved: %s  (%d .txt files + vvt.vvt)\n', folder_path, n_written);
end

% --------------------------

function [bx, by] = get_ball_pos(ev)
    bx = NaN; by = NaN;
    if ~isfield(ev,'ball') || isempty(ev.ball), return; end
    b = ev.ball;
    if isstruct(b) && numel(b) > 0
        bx = safe_num(b(1),'x');
        by = safe_num(b(1),'y');
    end
end

% --------------------------

function val = safe_num(st, field)
    if isfield(st,field) && ~isempty(st.(field))
        val = double(st.(field));
    else
        val = NaN;
    end
end

function val = safe_str(st, field)
    if isfield(st,field) && ~isempty(st.(field))
        val = char(st.(field));
    else
        val = '';
    end
end

function val = sn(x)
    if isnumeric(x) && ~isempty(x), val = double(x(1));
    elseif isnumeric(x),             val = NaN;
    else,                            val = x;
    end
end