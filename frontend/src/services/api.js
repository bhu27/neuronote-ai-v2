import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Default FastAPI port

export const uploadPdf = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_BASE_URL}/upload-pdf`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getSummary = async (mode) => {
  const response = await axios.get(`${API_BASE_URL}/summarize`, {
    params: { mode },
  });
  return response.data;
};

export const askQuestion = async (question) => {
  const response = await axios.post(`${API_BASE_URL}/chat`, { question });
  return response.data;
};

export const getMindmap = async () => {
  const response = await axios.get(`${API_BASE_URL}/mindmap`);
  return response.data;
};
