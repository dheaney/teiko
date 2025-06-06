import React, { useState, useEffect } from 'react';
import { 
  ChevronDownIcon, 
  AdjustmentsHorizontalIcon,
  ChartBarIcon,
  BeakerIcon,
  UserGroupIcon,
  FolderIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import {
  Transition,
  Switch
} from '@headlessui/react';
import { Fragment } from 'react';

import Plotly from 'plotly.js-dist-min';

// API Base URL - you'll need to update this to match your Flask server
const API_BASE_URL = 'http://localhost:5000/api';

// Custom hook for API calls
function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apiCall = async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setLoading(false);
      return data;
    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  };

  return { apiCall, loading, error };
}

// Loading spinner component
function LoadingSpinner() {
  return (
    <div className="flex justify-center items-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  );
}

// Pagination component
function Pagination({ currentPage, totalPages, onPageChange }) {
  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);
  
  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
      <div className="flex flex-1 justify-between sm:hidden">
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Previous
        </button>
        <button
          onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
          className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Next
        </button>
      </div>
      <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-gray-700">
            Page <span className="font-medium">{currentPage}</span> of{' '}
            <span className="font-medium">{totalPages}</span>
          </p>
        </div>
        <div>
          <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm">
            {pages.map((page) => (
              <button
                key={page}
                onClick={() => onPageChange(page)}
                className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                  page === currentPage
                    ? 'z-10 bg-blue-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                    : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-offset-0'
                } ${page === 1 ? 'rounded-l-md' : ''} ${page === totalPages ? 'rounded-r-md' : ''}`}
              >
                {page}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
}

// Filter component
function FilterPanel({ filters, onFiltersChange, entityType }) {
  const [isOpen, setIsOpen] = useState(false);

  const handleFilterChange = (key, value) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <AdjustmentsHorizontalIcon className="h-4 w-4 mr-2" />
        Filters
        <ChevronDownIcon className="h-4 w-4 ml-2" />
      </button>

      <Transition
        show={isOpen}
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <div className="absolute right-0 z-10 mt-2 w-80 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5">
          <div className="p-4 space-y-4">
            {entityType === 'subjects' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Condition</label>
                  <input
                    type="text"
                    value={filters.condition || ''}
                    onChange={(e) => handleFilterChange('condition', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    placeholder="e.g., Control, Treatment"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Sex</label>
                  <select
                    value={filters.sex || ''}
                    onChange={(e) => handleFilterChange('sex', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  >
                    <option value="">All</option>
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Min Age</label>
                    <input
                      type="number"
                      value={filters.min_age || ''}
                      onChange={(e) => handleFilterChange('min_age', e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Max Age</label>
                    <input
                      type="number"
                      value={filters.max_age || ''}
                      onChange={(e) => handleFilterChange('max_age', e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>
              </>
            )}
            
            {entityType === 'samples' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Treatment</label>
                  <input
                    type="number"
                    value={filters.treatment || ''}
                    onChange={(e) => handleFilterChange('treatment', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Response</label>
                  <select
                    value={filters.response || ''}
                    onChange={(e) => handleFilterChange('response', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  >
                    <option value="">All</option>
                    <option value="true">Positive</option>
                    <option value="false">Negative</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Sample Type</label>
                  <input
                    type="number"
                    value={filters.sample_type || ''}
                    onChange={(e) => handleFilterChange('sample_type', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Condition</label>
                  <select
                    value={filters.response || ''}
                    onChange={(e) => handleFilterChange('condition', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  >
                    <option value="healty">healthy</option>
                    <option value="melanoma">melanoma</option>
                    <option value="lung">lung</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">At Baseline Only</label>
                  <select
                    value={filters.response || ''}
                    onChange={(e) => handleFilterChange('time_from_treatment_start', e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  >
                    <option value="null">False</option>
                    <option value="0">True</option>
                  </select>
                </div>
              </>
            )}

            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  onFiltersChange({});
                  setIsOpen(false);
                }}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Clear
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  );
}

// Projects list component
function ProjectsList() {
  const [projects, setProjects] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [includeSamples, setIncludeSamples] = useState(false);
  const { apiCall, loading, error } = useApi();

  useEffect(() => {
    loadProjects();
  }, [currentPage, includeSamples]);

  const loadProjects = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '10',
        include_samples: includeSamples.toString()
      });
      
      const data = await apiCall(`/projects?${params}`);
      setProjects(data.projects);
      setTotalPages(data.pagination.pages);
    } catch (err) {
      console.error('Error loading projects:', err);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Projects</h2>
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <Switch
              checked={includeSamples}
              onChange={setIncludeSamples}
              className={`${
                includeSamples ? 'bg-blue-600' : 'bg-gray-200'
              } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
            >
              <span
                className={`${
                  includeSamples ? 'translate-x-6' : 'translate-x-1'
                } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
              />
            </Switch>
            <span className="ml-2 text-sm text-gray-700">Include Samples</span>
          </div>
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {projects.map((project) => (
            <li key={project.project_id}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <FolderIcon className="h-5 w-5 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-blue-600">
                        Project {project.project_id}
                      </p>
                      <p className="text-sm text-gray-500">
                        Created: {new Date(project.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  {includeSamples && project.samples && (
                    <div className="text-sm text-gray-500">
                      {project.samples.length} samples
                    </div>
                  )}
                </div>
                {includeSamples && project.samples && project.samples.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Samples:</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                      {project.samples.slice(0, 6).map((sample) => (
                        <div key={sample.sample_id} className="bg-gray-50 rounded px-2 py-1">
                          <span className="text-xs text-gray-600">
                            Sample {sample.sample_id} - Treatment {sample.treatment}
                          </span>
                        </div>
                      ))}
                      {project.samples.length > 6 && (
                        <div className="bg-gray-50 rounded px-2 py-1">
                          <span className="text-xs text-gray-600">
                            +{project.samples.length - 6} more
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
      />
    </div>
  );
}

// Subjects list component
function SubjectsList() {
  const [subjects, setSubjects] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({});
  const [includeSamples, setIncludeSamples] = useState(false);
  const { apiCall, loading, error } = useApi();

  useEffect(() => {
    loadSubjects();
  }, [currentPage, filters, includeSamples]);

  const loadSubjects = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '10',
        include_samples: includeSamples.toString(),
        ...filters
      });
      
      const data = await apiCall(`/subjects?${params}`);
      setSubjects(data.subjects);
      setTotalPages(data.pagination.pages);
    } catch (err) {
      console.error('Error loading subjects:', err);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Subjects</h2>
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <Switch
              checked={includeSamples}
              onChange={setIncludeSamples}
              className={`${
                includeSamples ? 'bg-blue-600' : 'bg-gray-200'
              } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
            >
              <span
                className={`${
                  includeSamples ? 'translate-x-6' : 'translate-x-1'
                } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
              />
            </Switch>
            <span className="ml-2 text-sm text-gray-700">Include Samples</span>
          </div>
          <FilterPanel
            filters={filters}
            onFiltersChange={setFilters}
            entityType="subjects"
          />
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {subjects.map((subject) => (
            <li key={subject.subject_id}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <UserGroupIcon className="h-5 w-5 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-blue-600">
                        Subject {subject.subject_id}
                      </p>
                      <div className="flex space-x-4 text-sm text-gray-500">
                        {subject.condition && <span>Condition: {subject.condition}</span>}
                        {subject.age && <span>Age: {subject.age}</span>}
                        {subject.sex && <span>Sex: {subject.sex}</span>}
                      </div>
                    </div>
                  </div>
                  {includeSamples && subject.samples && (
                    <div className="text-sm text-gray-500">
                      {subject.samples.length} samples
                    </div>
                  )}
                </div>
                {includeSamples && subject.samples && subject.samples.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Samples:</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                      {subject.samples.slice(0, 6).map((sample) => (
                        <div key={sample.sample_id} className="bg-gray-50 rounded px-2 py-1">
                          <span className="text-xs text-gray-600">
                            Sample {sample.sample_id} - {sample.response ? 'Positive' : 'Negative'}
                          </span>
                        </div>
                      ))}
                      {subject.samples.length > 6 && (
                        <div className="bg-gray-50 rounded px-2 py-1">
                          <span className="text-xs text-gray-600">
                            +{subject.samples.length - 6} more
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
      />
    </div>
  );
}

// Samples list component
function SamplesList() {
  const [samples, setSamples] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({});
  const [includeRelations, setIncludeRelations] = useState(false);
  const { apiCall, loading, error } = useApi();

  useEffect(() => {
    loadSamples();
  }, [currentPage, filters, includeRelations]);

  // Add this function to your SamplesList component
const handleDeleteSample = async (sampleId) => {
  try {
    await apiCall(`/samples/${sampleId}`, {
      method: 'DELETE'
    });
    
    // Refresh the samples list
    loadSamples();
  } catch (error) {
  }
};

  const loadSamples = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '10',
        include_relations: includeRelations.toString(),
        ...filters
      });
      
      const data = await apiCall(`/samples?${params}`);
      setSamples(data.samples);
      setTotalPages(data.pagination.pages);
    } catch (err) {
      console.error('Error loading samples:', err);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Samples</h2>
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <Switch
              checked={includeRelations}
              onChange={setIncludeRelations}
              className={`${
                includeRelations ? 'bg-blue-600' : 'bg-gray-200'
              } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
            >
              <span
                className={`${
                  includeRelations ? 'translate-x-6' : 'translate-x-1'
                } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
              />
            </Switch>
            <span className="ml-2 text-sm text-gray-700">Include Relations</span>
          </div>
          <FilterPanel
            filters={filters}
            onFiltersChange={setFilters}
            entityType="samples"
          />
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
  <ul className="divide-y divide-gray-200">
    {samples.map((sample) => (
      <li key={sample.sample_id}>
        <div className="px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <BeakerIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <p className="text-sm font-medium text-blue-600">
                  Sample {sample.sample_id}
                </p>
                <div className="flex space-x-4 text-sm text-gray-500">
                  <span>Treatment: {sample.treatment || 'N/A'}</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    sample.response 
                      ? 'bg-green-100 text-green-800' 
                      : sample.response === false 
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                  }`}>
                    {sample.response === null ? 'Unknown' : sample.response ? 'Positive' : 'Negative'}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Delete button */}
            <button
              onClick={() => handleDeleteSample(sample.sample_id)}
              className="flex-shrink-0 p-1 rounded-full text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors duration-200"
              title="Delete sample"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
          
          {/* Cell counts */}
          <div className="mt-3">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Cell Counts:</h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
              {sample.b_cell && (
                <div className="bg-blue-50 px-2 py-1 rounded">
                  <span className="text-blue-800">B-Cell: {sample.b_cell} ({Math.round(100*sample.b_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte))}%)</span>
                </div>
              )}
              {sample.cd8_t_cell && (
                <div className="bg-green-50 px-2 py-1 rounded">
                  <span className="text-green-800">CD8 T: {sample.cd8_t_cell} ({Math.round(100*sample.cd8_t_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte))}%)</span>
                </div>
              )}
              {sample.cd4_t_cell && (
                <div className="bg-yellow-50 px-2 py-1 rounded">
                  <span className="text-yellow-800">CD4 T: {sample.cd4_t_cell} ({Math.round(100*sample.cd4_t_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte))}%)</span>
                </div>
              )}
              {sample.nk_cell && (
                <div className="bg-purple-50 px-2 py-1 rounded">
                  <span className="text-purple-800">NK: {sample.nk_cell} ({Math.round(100*sample.nk_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte))}%)</span>
                </div>
              )}
              {sample.monocyte && (
                <div className="bg-red-50 px-2 py-1 rounded">
                  <span className="text-red-800">Mono: {sample.monocyte} ({Math.round(100*sample.monocyte / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte))}%)</span>
                </div>
              )}
            </div>
          </div>

          {/* Relations */}
          {includeRelations && (sample.project || sample.subject) && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex space-x-6 text-sm text-gray-500">
                {sample.project && (
                  <span>Project: {sample.project.project_id}</span>
                )}
                {sample.subject && (
                  <span>
                    Subject: {sample.subject.subject_id} 
                    {sample.subject.condition && ` (${sample.subject.condition})`}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </li>
    ))}
  </ul>
  <ul className="divide-y divide-gray-200">
    <li>
      <div className="px-4 py-4 sm:px-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-full h-full bg-blue-100 p-3 rounded-lg px-2 py-1">
                <div className="text-sm font-medium text-blue-800">Samples Per Project</div>
                <div className="text-xs text-blue-700">
                  {samples.map((sample) => sample.project ? sample.project.project_id : -1).filter((project_id, index, array) => project_id !== -1 && array.indexOf(project_id) === index).map((project_id) =>
                    <div>
                      Project {project_id}: {samples.filter(sample => sample.project && sample.project.project_id == project_id).length}
                    </div>
                  )}
                </div>
            </div>
            <div className="w-full h-full bg-blue-100 p-3 rounded-lg px-2 py-1">
                <div className="text-sm font-medium text-blue-800">Responders vs Non-Responders</div>
                <div className="text-xs text-blue-700">
                  <div>
                    Responders: {samples.map((sample) => sample.response ? sample.response : -1).filter((response) => response == true).length}
                  </div>
                  <div>
                    Non-Responders: {samples.map((sample) => sample.response ? sample.response : -1).filter((response) => response == false).length}
                  </div>
                </div>
            </div>
            <div className="w-full h-full bg-blue-100 p-3 rounded-lg px-2 py-1">
                <div className="text-sm font-medium text-blue-800">Males vs Females</div>
                <div className="text-xs text-blue-700">
                  <div>
                    Males: {samples.map((sample) => sample.subject ? sample.subject.sex : -1).filter((sex) => sex === 'M').length}
                  </div>
                  <div>
                    Females: {samples.map((sample) => sample.subject ? sample.subject.sex : -1).filter((sex) => sex === 'F').length}
                  </div>
                </div>
            </div>
          </div>
        </div>
      </div>
    </li>
  </ul>
</div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
      />
    </div>
  );
}

// Create Sample component
function CreateSample({ onSampleCreated }) {
  const [formData, setFormData] = useState({
    project_id: '',
    subject_id: '',
    treatment: '',
    response: '',
    sample_type: '',
    time_from_treatment_start: '',
    b_cell: '',
    cd8_t_cell: '',
    cd4_t_cell: '',
    nk_cell: '',
    monocyte: ''
  });
  
  const [availableProjects, setAvailableProjects] = useState([]);
  const [availableSubjects, setAvailableSubjects] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { apiCall } = useApi();

  // Load available projects and subjects when component mounts
  useEffect(() => {
    loadReferences();
  }, []);

  const loadReferences = async () => {
    try {
      const data = await apiCall('/samples/references');
      setAvailableProjects(data.projects || []);
      setAvailableSubjects(data.subjects || []);
    } catch (err) {
      setError('Failed to load projects and subjects');
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    setError(''); // Clear error when user types
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      // Prepare data for submission (convert empty strings to null, parse numbers)
      const submitData = {};
      
      // Required fields
      submitData.project_id = parseInt(formData.project_id);
      submitData.subject_id = parseInt(formData.subject_id);
      
      // Optional fields - only include if not empty
      if (formData.treatment) submitData.treatment = parseInt(formData.treatment);
      if (formData.response !== '') submitData.response = formData.response === 'true';
      if (formData.sample_type) submitData.sample_type = parseInt(formData.sample_type);
      if (formData.time_from_treatment_start) submitData.time_from_treatment_start = parseInt(formData.time_from_treatment_start);
      if (formData.b_cell) submitData.b_cell = parseInt(formData.b_cell);
      if (formData.cd8_t_cell) submitData.cd8_t_cell = parseInt(formData.cd8_t_cell);
      if (formData.cd4_t_cell) submitData.cd4_t_cell = parseInt(formData.cd4_t_cell);
      if (formData.nk_cell) submitData.nk_cell = parseInt(formData.nk_cell);
      if (formData.monocyte) submitData.monocyte = parseInt(formData.monocyte);

      await apiCall('/samples', {
        method: 'POST',
        body: JSON.stringify(submitData)
      });

      // Reset form
      setFormData({
        project_id: '',
        subject_id: '',
        treatment: '',
        response: '',
        sample_type: '',
        time_from_treatment_start: '',
        b_cell: '',
        cd8_t_cell: '',
        cd4_t_cell: '',
        nk_cell: '',
        monocyte: ''
      });
      
      onSampleCreated?.();
      
    } catch (err) {
      setError(err.message || 'Failed to create sample');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setFormData({
      project_id: '',
      subject_id: '',
      treatment: '',
      response: '',
      sample_type: '',
      time_from_treatment_start: '',
      b_cell: '',
      cd8_t_cell: '',
      cd4_t_cell: '',
      nk_cell: '',
      monocyte: ''
    });
    setError('');
  };

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-lg font-medium leading-6 text-gray-900 mb-6">
        Create New Sample
      </h3>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Required Fields */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Required Information</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.project_id}
                onChange={(e) => handleInputChange('project_id', e.target.value)}
                required
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="">Select a project</option>
                {availableProjects.map((project) => (
                  <option key={project.project_id} value={project.project_id}>
                    Project {project.project_id} ({new Date(project.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subject <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.subject_id}
                onChange={(e) => handleInputChange('subject_id', e.target.value)}
                required
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="">Select a subject</option>
                {availableSubjects.map((subject) => (
                  <option key={subject.subject_id} value={subject.subject_id}>
                    Subject {subject.subject_id}
                    {subject.condition && ` (${subject.condition})`}
                    {subject.age && ` - Age ${subject.age}`}
                    {subject.sex && ` - ${subject.sex}`}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Treatment Information */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Treatment Information</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Treatment
              </label>
              <input
                type="number"
                value={formData.treatment}
                onChange={(e) => handleInputChange('treatment', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Response
              </label>
              <select
                value={formData.response}
                onChange={(e) => handleInputChange('response', e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="">Select response</option>
                <option value="true">Positive</option>
                <option value="false">Negative</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sample Type
              </label>
              <input
                type="number"
                value={formData.sample_type}
                onChange={(e) => handleInputChange('sample_type', e.target.value)}
                min="1"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 1"
              />
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time from Treatment Start (days)
              </label>
              <input
                type="number"
                value={formData.time_from_treatment_start}
                onChange={(e) => handleInputChange('time_from_treatment_start', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 7"
              />
            </div>
          </div>
        </div>

        {/* Cell Counts */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Cell Counts</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                B-Cell Count
              </label>
              <input
                type="number"
                value={formData.b_cell}
                onChange={(e) => handleInputChange('b_cell', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 150"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CD8 T-Cell Count
              </label>
              <input
                type="number"
                value={formData.cd8_t_cell}
                onChange={(e) => handleInputChange('cd8_t_cell', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CD4 T-Cell Count
              </label>
              <input
                type="number"
                value={formData.cd4_t_cell}
                onChange={(e) => handleInputChange('cd4_t_cell', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 300"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                NK Cell Count
              </label>
              <input
                type="number"
                value={formData.nk_cell}
                onChange={(e) => handleInputChange('nk_cell', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Monocyte Count
              </label>
              <input
                type="number"
                value={formData.monocyte}
                onChange={(e) => handleInputChange('monocyte', e.target.value)}
                min="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="e.g., 100"
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-6 border-t">
          <button
            type="button"
            onClick={handleReset}
            disabled={isSubmitting}
            className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            Reset
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !formData.project_id || !formData.subject_id}
            className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {isSubmitting ? 'Creating...' : 'Create Sample'}
          </button>
        </div>
      </form>
    </div>
  );
}

// Analytics component
function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [samplesDataBCell, setSamplesDataBCell] = useState([]);
  const [samplesDataCD8TCell, setSamplesDataCD8TCell] = useState([]);
  const [samplesDataCD4TCell, setSamplesDataCD4TCell] = useState([]);
  //const [samplesDataNKCell, setSamplesDataNKCell] = useState([]);
  const { apiCall, loading, error } = useApi();

  useEffect(() => {
    loadAnalytics();
    loadSamplesForPlot();
  }, []);

  const loadAnalytics = async () => {
    try {
      const data = await apiCall('/analytics/summary');
      setAnalytics(data);
    } catch (err) {
      console.error('Error loading analytics:', err);
    }
  };

  const loadSamplesForPlot = async () => {
    try {
      // Get all samples with b_cell data and response info
      const data = await apiCall('/samples?per_page=1000&include_relations=true');
      const samplesWithBCell = data.samples.filter(sample => 
        sample.b_cell !== null && 
        sample.b_cell !== undefined && 
        sample.response !== null && 
        sample.response !== undefined &&
        sample.subject.condition == "melanoma" &&
        sample.treatment == 1 &&
        sample.sample_type == 1
      );

      const samplesWithCD8TCell = data.samples.filter(sample => 
        sample.cd8_t_cell !== null && 
        sample.cd8_t_cell !== undefined && 
        sample.response !== null && 
        sample.response !== undefined &&
        sample.subject.condition == "melanoma" &&
        sample.treatment == 1 &&
        sample.sample_type == 1
      );

      const samplesWithCD4TCell = data.samples.filter(sample => 
        sample.cd4_t_cell !== null && 
        sample.cd4_t_cell !== undefined && 
        sample.response !== null && 
        sample.response !== undefined &&
        sample.subject.condition == "melanoma" &&
        sample.treatment == 1 &&
        sample.sample_type == 1
      );
      
      setSamplesDataBCell(samplesWithBCell);
      setSamplesDataCD8TCell(samplesWithCD8TCell);
      setSamplesDataCD4TCell(samplesWithCD4TCell);

    } catch (err) {
      console.error('Error loading samples for plot:', err);
    }
  };

  const sample_attr_map = (sample, name) => {
    if(name === 'bcell') {
      return Math.round(100*sample.b_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte));
    } else if(name === 'cd8') {
      return Math.round(100*sample.cd8_t_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte));
    } else {
      return Math.round(100*sample.cd4_t_cell / (sample.b_cell + sample.cd8_t_cell + sample.cd4_t_cell + sample.nk_cell + sample.monocyte));
    }
  }

  const quantile = (arr, q) => {
    if (arr.length === 0) {
      return NaN;
    }
    const sorted = arr.sort();
    const pos = (sorted.length - 1) * q;
    const base = Math.floor(pos);
    const rest = pos - base;
    if (sorted[base + 1] !== undefined) {
      return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
    } else {
      return sorted[base];
    }
  }

  const createBoxPlot = (samplesData, name) => {
    if (!samplesData || samplesData.length === 0) return;

    // Separate data by response status
    const responders = samplesData.filter(sample => sample.response === true);
    const nonResponders = samplesData.filter(sample => sample.response === false);

    const respondersY = responders.map(sample => sample_attr_map(sample, name));
    const nonRespondersY = nonResponders.map(sample => sample_attr_map(sample, name));

    const data = [
      {
        y: respondersY,
        type: 'box',
        name: 'Responders',
        marker: { color: '#10B981' }, // Green
        boxpoints: 'outliers',
        jitter: 0.3,
        pointpos: -1.8
      },
      {
        y: nonRespondersY,
        type: 'box',
        name: 'Non-Responders',
        marker: { color: '#EF4444' }, // Red
        boxpoints: 'outliers',
        jitter: 0.3,
        pointpos: -1.8
      }
    ];

    const layout = {
      title: {
        // text: 'B-Cell Counts by Response Status',
        font: { size: 16, color: '#1F2937' }
      },
      yaxis: {
        title: 'B-Cell Count',
        titlefont: { color: '#6B7280' },
        tickfont: { color: '#6B7280' }
      },
      xaxis: {
        titlefont: { color: '#6B7280' },
        tickfont: { color: '#6B7280' }
      },
      plot_bgcolor: 'rgba(0,0,0,0)',
      paper_bgcolor: 'rgba(0,0,0,0)',
      font: { family: 'Inter, system-ui, sans-serif' },
      margin: { l: 60, r: 40, t: 50, b: 60 },
      showlegend: true,
      legend: {
        orientation: 'h',
        x: 0.5,
        xanchor: 'center',
        y: -0.2
      }
    };

    const config = {
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
      responsive: true
    };

    // Use Plotly to create the plot
    const plotDiv = document.getElementById(name + '-boxplot');
    const reportDiv = document.getElementById(name + '-report');

    if (plotDiv && Plotly) {
      Plotly.newPlot(name + '-boxplot', data, layout, config);
    }
  };

  useEffect(() => {
    if (samplesDataBCell.length > 0) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        createBoxPlot(samplesDataBCell, 'bcell');
      }, 100);
    }
    if (samplesDataCD8TCell.length > 0) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        createBoxPlot(samplesDataCD8TCell, 'cd8');
      }, 100);
    }
    if (samplesDataCD4TCell.length > 0) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        createBoxPlot(samplesDataCD4TCell, 'cd4');
      }, 100);
    }
  }, [samplesDataBCell, samplesDataCD8TCell, samplesDataCD4TCell]);

  if (loading) return <LoadingSpinner />;
  if (!analytics) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h2>
      
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <UserGroupIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Projects</dt>
                  <dd className="text-lg font-medium text-gray-900">{analytics.summary.total_projects}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <UserGroupIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Subjects</dt>
                  <dd className="text-lg font-medium text-gray-900">{analytics.summary.total_subjects}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <BeakerIcon className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Samples</dt>
                  <dd className="text-lg font-medium text-gray-900">{analytics.summary.total_samples}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Response by treatment chart */}
      {analytics.response_by_treatment && analytics.response_by_treatment.length > 0 && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Response Rates by Treatment
            </h3>
            <div className="space-y-4">
              {analytics.response_by_treatment.map((item) => (
                <div key={item.treatment} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-blue-600">{item.treatment}</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Treatment {item.treatment}</p>
                      <p className="text-sm text-gray-500">
                        {item.positive_responses} / {item.total_samples} samples responded
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${(item.response_rate * 100).toFixed(1)}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-gray-900">
                      {(item.response_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* B-Cell Analysis Box Plot */}
      {samplesDataBCell.length > 0 && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  B-Cell Distribution Analysis
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  Box plot showing B-cell count distribution for responders vs non-responders
                </p>
              </div>
              <div className="text-sm text-gray-500">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {samplesDataBCell.length} samples
                </span>
              </div>
            </div>
            
            {/* Plotly container */}
            <div className="w-full h-96">
              <div id="bcell-boxplot" className="w-full h-full"></div>
            </div>
            <div className="w-full h-26">
              <div id="bcell-report" className="w-full h-full bg-blue-100 p-3 rounded-lg">
                <div className="text-sm font-medium text-blue-800">Distributions Separated</div>
                <div className="text-xs text-blue-700">
                  {
                    (
                      quantile(samplesDataBCell.filter(sample => sample.response === true).map(sample => sample_attr_map(sample, 'bcell')), 0.1) >
                      quantile(samplesDataBCell.filter(sample => sample.response === false).map(sample => sample_attr_map(sample, 'bcell')), 0.9)
                    ) || (
                      quantile(samplesDataBCell.filter(sample => sample.response === true).map(sample => sample_attr_map(sample, 'bcell')), 0.9) <
                      quantile(samplesDataBCell.filter(sample => sample.response === false).map(sample => sample_attr_map(sample, 'bcell')), 0.1)
                    ) ? 'True' : 'False'
                  }
                </div>
              </div>
            </div>
            
            {/* Summary statistics */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="text-sm font-medium text-green-900">Responders</div>
                <div className="text-xs text-green-700">
                  {samplesDataBCell.filter(s => s.response === true).length} samples
                  {samplesDataBCell.filter(s => s.response === true).length > 0 && (
                    <span className="ml-2">
                      (avg: {Math.round(
                        samplesDataBCell.filter(s => s.response === true)
                          .reduce((sum, s) => sum + sample_attr_map(s, 'bcell'), 0) / 
                        samplesDataBCell.filter(s => s.response === true).length
                      )})
                    </span>
                  )}
                </div>
              </div>
              <div className="bg-red-50 p-3 rounded-lg">
                <div className="text-sm font-medium text-red-900">Non-Responders</div>
                <div className="text-xs text-red-700">
                  {samplesDataBCell.filter(s => s.response === false).length} samples
                  {samplesDataBCell.filter(s => s.response === false).length > 0 && (
                    <span className="ml-2">
                      (avg: {Math.round(
                        samplesDataBCell.filter(s => s.response === false)
                          .reduce((sum, s) => sum + sample_attr_map(s, 'bcell'), 0) / 
                        samplesDataBCell.filter(s => s.response === false).length
                      )})
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CD8 T-Cell Analysis Box Plot */}
      {samplesDataCD8TCell.length > 0 && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  CD8 T-Cell Distribution Analysis
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  Box plot showing CD8 T-cell count distribution for responders vs non-responders
                </p>
              </div>
              <div className="text-sm text-gray-500">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {samplesDataCD8TCell.length} samples
                </span>
              </div>
            </div>
            
            {/* Plotly container */}
            <div className="w-full h-96">
              <div id="cd8-boxplot" className="w-full h-full"></div>
            </div>
            <div className="w-full h-26">
              <div id="bcell-report" className="w-full h-full bg-blue-100 p-3 rounded-lg">
                <div className="text-sm font-medium text-blue-800">Distributions Separated</div>
                <div className="text-xs text-blue-700">
                  {
                    (
                      quantile(samplesDataCD8TCell.filter(sample => sample.response === true).map(sample => sample_attr_map(sample, 'cd8')), 0.1) >
                      quantile(samplesDataCD8TCell.filter(sample => sample.response === false).map(sample => sample_attr_map(sample, 'cd8')), 0.9)
                    ) || (
                      quantile(samplesDataCD8TCell.filter(sample => sample.response === true).map(sample => sample_attr_map(sample, 'cd8')), 0.9) <
                      quantile(samplesDataCD8TCell.filter(sample => sample.response === false).map(sample => sample_attr_map(sample, 'cd8')), 0.1)
                    ) ? 'True' : 'False'
                  }
                </div>
              </div>
            </div>
            
            {/* Summary statistics */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="text-sm font-medium text-green-900">Responders</div>
                <div className="text-xs text-green-700">
                  {samplesDataCD8TCell.filter(s => s.response === true).length} samples
                  {samplesDataCD8TCell.filter(s => s.response === true).length > 0 && (
                    <span className="ml-2">
                      (avg: {Math.round(
                        samplesDataCD8TCell.filter(s => s.response === true)
                          .reduce((sum, s) => sum + sample_attr_map(s, 'cd8'), 0) / 
                        samplesDataCD8TCell.filter(s => s.response === true).length
                      )})
                    </span>
                  )}
                </div>
              </div>
              <div className="bg-red-50 p-3 rounded-lg">
                <div className="text-sm font-medium text-red-900">Non-Responders</div>
                <div className="text-xs text-red-700">
                  {samplesDataCD8TCell.filter(s => s.response === false).length} samples
                  {samplesDataCD8TCell.filter(s => s.response === false).length > 0 && (
                    <span className="ml-2">
                      (avg: {Math.round(
                        samplesDataCD8TCell.filter(s => s.response === false)
                          .reduce((sum, s) => sum + sample_attr_map(s, 'cd8'), 0) / 
                        samplesDataCD8TCell.filter(s => s.response === false).length
                      )})
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CD4 T-Cell Analysis Box Plot */}
      {samplesDataCD4TCell.length > 0 && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  CD4 T-Cell Distribution Analysis
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  Box plot showing CD4 T-cell count distribution for responders vs non-responders
                </p>
              </div>
              <div className="text-sm text-gray-500">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {samplesDataCD4TCell.length} samples
                </span>
              </div>
            </div>
            
            {/* Plotly container */}
            <div className="w-full h-96">
              <div id="cd4-boxplot" className="w-full h-full"></div>
            </div>
                        <div className="w-full h-26">
              <div id="bcell-report" className="w-full h-full bg-blue-100 p-3 rounded-lg">
                <div className="text-sm font-medium text-blue-800">Distributions Separated</div>
                <div className="text-xs text-blue-700">
                  {
                    (
                      quantile(samplesDataCD4TCell.filter(sample => sample.response === true).map(sample => sample_attr_map(sample, 'cd4')), 0.1) >
                      quantile(samplesDataCD4TCell.filter(sample => sample.response === false).map(sample => sample_attr_map(sample, 'cd4')), 0.9)
                    ) || (
                      quantile(samplesDataCD4TCell.filter(sample => sample.response === true).map(sample => sample_attr_map(sample, 'cd4')), 0.9) <
                      quantile(samplesDataCD4TCell.filter(sample => sample.response === false).map(sample => sample_attr_map(sample, 'cd4')), 0.1)
                    ) ? 'True' : 'False'
                  }
                </div>
              </div>
            </div>
            
            {/* Summary statistics */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="text-sm font-medium text-green-900">Responders</div>
                <div className="text-xs text-green-700">
                  {samplesDataCD4TCell.filter(s => s.response === true).length} samples
                  {samplesDataCD4TCell.filter(s => s.response === true).length > 0 && (
                    <span className="ml-2">
                      (avg: {Math.round(
                        samplesDataCD4TCell.filter(s => s.response === true)
                          .reduce((sum, s) => sum + sample_attr_map(s, 'cd4'), 0) / 
                        samplesDataCD4TCell.filter(s => s.response === true).length
                      )})
                    </span>
                  )}
                </div>
              </div>
              <div className="bg-red-50 p-3 rounded-lg">
                <div className="text-sm font-medium text-red-900">Non-Responders</div>
                <div className="text-xs text-red-700">
                  {samplesDataCD4TCell.filter(s => s.response === false).length} samples
                  {samplesDataCD4TCell.filter(s => s.response === false).length > 0 && (
                    <span className="ml-2">
                      (avg: {Math.round(
                        samplesDataCD4TCell.filter(s => s.response === false)
                          .reduce((sum, s) => sum + sample_attr_map(s, 'cd4'), 0) / 
                        samplesDataCD4TCell.filter(s => s.response === false).length
                      )})
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sex distribution */}
      {analytics.sex_distribution && analytics.sex_distribution.length > 0 && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Subject Distribution by Sex
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {analytics.sex_distribution.map((item) => (
                <div key={item.sex} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-4 h-4 rounded-full ${
                      item.sex === 'M' ? 'bg-blue-500' : item.sex === 'F' ? 'bg-pink-500' : 'bg-gray-500'
                    }`}></div>
                    <span className="text-sm font-medium text-gray-900">
                      {item.sex === 'M' ? 'Male' : item.sex === 'F' ? 'Female' : 'Other'}
                    </span>
                  </div>
                  <span className="text-lg font-semibold text-gray-900">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Main App component
function App() {
  const [activeTab, setActiveTab] = useState(0);

  const tabs = [
    { name: 'Analytics', icon: ChartBarIcon, component: Analytics },
    { name: 'Projects', icon: FolderIcon, component: ProjectsList },
    { name: 'Subjects', icon: UserGroupIcon, component: SubjectsList },
    { name: 'Samples', icon: BeakerIcon, component: SamplesList },
    { name: 'Create Sample', icon: BeakerIcon, component: CreateSample },
  ];

  const ActiveComponent = tabs[activeTab].component;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <BeakerIcon className="h-8 w-8 text-blue-600" />
                <span className="ml-2 text-xl font-bold text-gray-900">Research Dashboard</span>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                Connected to: {API_BASE_URL}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Tab navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.name}
                  onClick={() => setActiveTab(index)}
                  className={`${
                    activeTab === index
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{tab.name}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ActiveComponent />
      </main>
    </div>
  );
}

export default App;
