from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class CodeAnalysis(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    project_name  = db.Column(db.String(255), nullable=False)
    upload_type   = db.Column(db.String(50))
    source        = db.Column(db.String(500))
    total_files   = db.Column(db.Integer)
    total_lines   = db.Column(db.Integer)
    total_functions = db.Column(db.Integer)
    metrics_json  = db.Column(db.Text)
    issues_json   = db.Column(db.Text)
    quality_score = db.Column(db.Float)
    analysis      = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':             self.id,
            'project_name':   self.project_name,
            'upload_type':    self.upload_type,
            'source':         self.source,
            'total_files':    self.total_files,
            'total_lines':    self.total_lines,
            'total_functions':self.total_functions,
            'quality_score':  self.quality_score,
            'metrics':        json.loads(self.metrics_json)  if self.metrics_json  else {},
            'issues':         json.loads(self.issues_json)   if self.issues_json   else [],
            'analysis':       self.analysis,
            'created_at':     self.created_at.isoformat()
        }