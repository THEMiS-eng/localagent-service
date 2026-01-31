import React, { useState, useEffect } from 'react';
import './SkillSelector.css';

const SkillSelector = ({ onSkillSelect, selectedSkill, skills = [] }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredSkills = skills.filter(skill =>
    skill.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSkillSelect = (skill) => {
    onSkillSelect(skill);
    setIsOpen(false);
    setSearchTerm('');
  };

  const handleToggle = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="skill-selector">
      <div className="skill-selector-header" onClick={handleToggle}>
        <span className="selected-skill">
          {selectedSkill ? selectedSkill.name : 'Select a skill...'}
        </span>
        <span className={`dropdown-arrow ${isOpen ? 'open' : ''}`}>▼</span>
      </div>
      
      {isOpen && (
        <div className="skill-dropdown">
          <input
            type="text"
            placeholder="Search skills..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="skill-search"
          />
          <div className="skill-list">
            {filteredSkills.map((skill) => (
              <div
                key={skill.id}
                className={`skill-item ${selectedSkill?.id === skill.id ? 'selected' : ''}`}
                onClick={() => handleSkillSelect(skill)}
              >
                <span className="skill-name">{skill.name}</span>
                <span className="skill-description">{skill.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillSelector;