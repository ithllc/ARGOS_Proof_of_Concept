export enum TaskStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed"
}

export interface ResearchTask {
  id: string;
  description: string;
  status: TaskStatus;
}

export interface ResearchPaper {
  title: string;
  url: string;
  summary?: string;
}

export interface ResearchState {
  query: string;
  tasks: ResearchTask[];
  papers: ResearchPaper[];
  analysis: string;
  status: string;
}
