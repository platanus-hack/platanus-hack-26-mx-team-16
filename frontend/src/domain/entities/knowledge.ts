export interface Knowledge {
  uuid: string;
  name: string;
  description: string;
  docCount: number;
  totalDocs: number;
  status: string[];
  updatedAt: string;
  owner: {
    name: string;
    avatar?: string;
  };
}
