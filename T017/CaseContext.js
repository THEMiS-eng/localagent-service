import React from 'react';
import './CaseContext.css';

const CaseContext = ({ caseData, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="case-context loading">
        <div className="loading-spinner"></div>
        <span>Loading case context...</span>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="case-context empty">
        <span>No case selected</span>
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'green';
      case 'pending': return 'orange';
      case 'closed': return 'gray';
      default: return 'blue';
    }
  };

  return (
    <div className="case-context">
      <div className="case-header">
        <h3 className="case-title">{caseData.title}</h3>
        <span 
          className={`case-status ${getStatusColor(caseData.status)}`}
        >
          {caseData.status}
        </span>
      </div>
      
      <div className="case-metadata">
        <div className="metadata-item">
          <label>Case ID:</label>
          <span>{caseData.id}</span>
        </div>
        <div className="metadata-item">
          <label>Priority:</label>
          <span className={`priority-${caseData.priority?.toLowerCase()}`}>
            {caseData.priority}
          </span>
        </div>
        <div className="metadata-item">
          <label>Created:</label>
          <span>{new Date(caseData.createdAt).toLocaleDateString()}</span>
        </div>
      </div>
      
      {caseData.description && (
        <div className="case-description">
          <label>Description:</label>
          <p>{caseData.description}</p>
        </div>
      )}
    </div>
  );
};

export default CaseContext;