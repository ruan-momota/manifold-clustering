function lapd_run(kind, input_file, output_file, lapd_root, mode)
% Run one LAPD dataset and save labels, parameters, diagnostics, and provenance.
% kind: 'coil20', 'usps', or 'openml'; mode: 'known' or 'estimate'.

start_dir = pwd;
input_file = absolute_path(input_file, start_dir);
output_file = absolute_path(output_file, start_dir);
lapd_root = absolute_path(lapd_root, start_dir);

if ~isfile(input_file), error('Input file missing: %s', input_file); end
if ~isfolder(lapd_root), error('LAPD directory missing: %s', lapd_root); end
if ~strcmp(mode, 'known') && ~strcmp(mode, 'estimate')
    error('mode must be known or estimate');
end

data = load(input_file);
if ~isfield(data, 'X') || ~isfield(data, 'labelsGT')
    error('Input must contain X and labelsGT');
end
X = double(data.X);
labelsGT = data.labelsGT(:);
if size(X, 1) ~= numel(labelsGT) || any(~isfinite(X(:)))
    error('Invalid X shape, labels, or nonfinite values');
end

switch lower(kind)
    case 'coil20'
        keep = ismember(labelsGT, 1:20);
        X = X(keep, :);
        labelsGT = labelsGT(keep);
        sample_indices = find(keep) - 1;
        opts.intrdim = 1;
        opts.epsilon = 0;
        opts.bandwidth = 22;
        opts.weight = 'two sided';
    case 'usps'
        keep = ismember(labelsGT, 0:9);
        X = X(keep, :);
        labelsGT = labelsGT(keep);
        sample_indices = find(keep) - 1;
        opts.intrdim = 2;
        opts.epsilon = 0;
        opts.bandwidth = 17;
        opts.weight = 'two sided';
        opts.filter = 1.3;
        opts.componentsize = 0.008;
    case 'openml'
        if ~isfield(data, 'sample_indices') || ~isfield(data, 'openml_id')
            error('OpenML input must contain sample_indices and openml_id');
        end
        sample_indices = data.sample_indices(:);
        if numel(sample_indices) ~= size(X, 1) || ...
                any(sample_indices ~= (0:size(X, 1)-1)')
            error('OpenML sample order mismatch');
        end
        opts.intrdim = 1;
        opts.epsilon = 0;
        opts.bandwidth = 10;
        opts.knnnumber = min(size(X, 1), max(100, ceil(0.1 * size(X, 1)) + opts.bandwidth));
        opts.weight = 'two sided';
    otherwise
        error('kind must be coil20, usps, or openml');
end

if isempty(X), error('No samples remain after subset selection'); end
if strcmp(mode, 'known'), opts.K = numel(unique(labelsGT)); end
opts.parallel = 0;

cd(lapd_root);
restore_dir = onCleanup(@() cd(start_dir));
addpath(genpath(lapd_root));
[git_status, lapd_commit] = system('git rev-parse HEAD');
if git_status ~= 0, lapd_commit = 'unknown'; end
lapd_commit = strtrim(lapd_commit);
matlab_version = version;

fprintf('LAPD %s %s: %d samples, %d features\n', kind, mode, size(X, 1), size(X, 2));
[intrinsic_dim, epsilon, k_hat, predicted_labels, runtime, misc] = main(X, opts);
predicted_labels = predicted_labels(:);
if numel(predicted_labels) ~= size(X, 1)
    error('LAPD returned %d labels for %d samples', numel(predicted_labels), size(X, 1));
end

if strcmpi(kind, 'openml')
    openml_id = double(data.openml_id);
    embedding_variant = char(data.embedding_variant);
    clustering_accuracy = NaN;
else
    openml_id = NaN;
    embedding_variant = 'original_benchmark';
    clustering_accuracy = accuracy(predicted_labels, labelsGT);
end

output_dir = fileparts(output_file);
if ~isfolder(output_dir), mkdir(output_dir); end
save(output_file, 'kind', 'mode', 'input_file', 'sample_indices', ...
    'labelsGT', 'predicted_labels', 'opts', 'intrinsic_dim', 'epsilon', ...
    'k_hat', 'runtime', 'misc', 'openml_id', 'embedding_variant', ...
    'clustering_accuracy', 'matlab_version', 'lapd_commit', '-v7');
fprintf('Saved %s; k_hat=%d; runtime=%.3f s; accuracy=%.4f\n', ...
    output_file, k_hat, runtime, clustering_accuracy);
end

function result = absolute_path(path_value, base_dir)
if startsWith(path_value, filesep)
    result = path_value;
else
    result = fullfile(base_dir, path_value);
end
end
