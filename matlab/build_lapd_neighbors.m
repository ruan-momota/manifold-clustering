function build_lapd_neighbors()
% Build the OpenTSTOOL neighbor functions missing from LAPD on Linux.
project_root = fileparts(fileparts(mfilename('fullpath')));
source_dir = fullfile(project_root, 'data', 'runtime_libs', ...
    'opentstool_src', 'OpenTSTOOL', 'mex-dev', 'NN');
output_dir = fullfile(project_root, 'vendor', 'LAPD', 'Auxiliary', ...
    'MSVD', 'DiffusionGeometry', 'NearestNeighbors');

start_dir = pwd;
restore_dir = onCleanup(@() cd(start_dir));
cd(source_dir);
% Qualify an inherited member for modern C++ template lookup.
header_file = fullfile(source_dir, '..', 'NNSearcher', 'nearneigh_search.h');
header = fileread(header_file);
header = strrep(header, 'root.center = randindex(Nused);', ...
    'root.center = this->randindex(Nused);');
if ~contains(header, 'using nearneigh_searcher<POINT_SET>::test;')
    header = strrep(header, 'using nearneigh_searcher<POINT_SET>::Nused;', ...
        ['using nearneigh_searcher<POINT_SET>::Nused;' newline ...
         '    using nearneigh_searcher<POINT_SET>::test;']);
end
fid = fopen(header_file, 'w');
fprintf(fid, '%s', header);
fclose(fid);

% Check radius values, rather than comparing their pointer with zero.
range_file = fullfile(source_dir, 'range_search.cpp');
range_source = fileread(range_file);
range_source = regexprep(range_source, ...
    'if \(range<0\) \{\s*mexErrMsgTxt\("Range must be positive"\);\s*return;\s*\}', ...
    ['for (long i = 0; i < N_range; ++i) {' newline ...
     '        if (range[i] < 0) {' newline ...
     '            mexErrMsgTxt("Range must be positive");' newline ...
     '            return;' newline ...
     '        }' newline ...
     '    }']);
fid = fopen(range_file, 'w');
fprintf(fid, '%s', range_source);
fclose(fid);

names = {'nn_prepare', 'nn_search', 'range_search'};
for i = 1:numel(names)
    fprintf('Compiling %s\n', names{i});
    mex('-O', '-I.', '-I..', '-DPARTIAL_SEARCH', '-compatibleArrayDims', ...
        'CXXFLAGS=$CXXFLAGS -std=c++11 -include cstring', ...
        [names{i} '.cpp'], '-outdir', output_dir);
end

addpath(output_dir);
clear nn_prepare nn_search range_search;
disp(which('nn_prepare'));
disp(which('nn_search'));
disp(which('range_search'));

% Check the compiled search against MATLAB on a small set without distance ties.
rng('default');
X = rand(20, 3);
atria = nn_prepare(X);
[indices, distances] = nn_search(X, atria, X(1:3, :), 3);
[expected_indices, expected_distances] = knnsearch(X, X(1:3, :), 'K', 3);
assert(isequal(indices, expected_indices));
assert(max(abs(distances(:) - expected_distances(:))) < 1e-10);
radii = [0.2; 0.4; 0.6];
counts = range_search(X, atria, X(1:3, :), radii);
expected_counts = sum(pdist2(X(1:3, :), X) <= radii, 2);
assert(isequal(counts, expected_counts));
fprintf('Neighbor search check passed.\n');
end
