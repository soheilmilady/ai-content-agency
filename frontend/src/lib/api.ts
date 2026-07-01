import axios from "axios";
import Cookies from "js-cookie";

export interface User {
  id: number;
  email: string;
  username: string;
  role: string;
  can_publish: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Article {
  id: number;
  title: string;
  content_html: string;
  meta_description: string;
  focus_keyword: string;
  seo_score: number;
  status: string;
  author: { id: number; username: string };
  last_modified_by?: { id: number; username: string } | null;
  assigned_editors: { id: number; username: string }[];
  created_at: string;
  updated_at: string;
}

export interface UserCreateData {
  email: string;
  username: string;
  password: string;
  role?: string;
  can_publish?: boolean;
}

export interface UserUpdateData {
  email?: string;
  username?: string;
  role?: string;
  can_publish?: boolean;
  is_active?: boolean;
}

export interface ProfileUpdateData {
  email?: string;
  username?: string;
  current_password?: string;
  new_password?: string;
}

export interface ArticleUpdateData {
  title?: string;
  content_html?: string;
  meta_description?: string;
  status?: string;
}

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      Cookies.remove("auth_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export async function login(
  email: string,
  password: string
): Promise<{ access_token: string }> {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);
  
  const { data } = await api.post<{ access_token: string; token_type: string }>(
    "/auth/login",
    params,
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );
  return { access_token: data.access_token };
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

export async function updateProfile(data: ProfileUpdateData): Promise<User> {
  const { data: user } = await api.patch<User>("/auth/me", data);
  return user;
}

export async function getUsers(): Promise<User[]> {
  const { data } = await api.get<User[]>("/users");
  return data;
}

export async function createUser(userData: UserCreateData): Promise<User> {
  const { data } = await api.post<User>("/users", userData);
  return data;
}

export async function updateUser(
  id: number,
  userData: UserUpdateData
): Promise<User> {
  const { data } = await api.put<User>(`/users/${id}`, userData);
  return data;
}

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}

export async function generateArticle(
  topic: string,
  keyword: string,
  model?: string
): Promise<Article> {
  const { data } = await api.post<Article>("/articles/generate", {
    topic,
    keyword,
    llm_model: model,
  });
  return data;
}

export async function getArticle(id: number): Promise<Article> {
  const { data } = await api.get<Article>(`/articles/${id}`);
  return data;
}

export async function getArticles(): Promise<Article[]> {
  const { data } = await api.get<Article[]>("/articles");
  return data;
}

export async function publishArticle(id: number): Promise<Article> {
  const { data } = await api.post<Article>(`/articles/${id}/publish`, {});
  return data;
}

export async function approveArticle(id: number): Promise<Article> {
  const { data } = await api.post<Article>(`/articles/${id}/approve`, {});
  return data;
}

export async function updateArticle(
  id: number,
  articleData: ArticleUpdateData
): Promise<Article> {
  const { data } = await api.patch<Article>(`/articles/${id}`, articleData);
  return data;
}

export async function deleteArticle(id: number): Promise<void> {
  await api.delete(`/articles/${id}`);
}

export async function assignEditors(id: number, editor_ids: number[]): Promise<Article> {
  const { data } = await api.post<Article>(`/articles/${id}/assign`, { editor_ids });
  return data;
}

export async function improveArticlePreview(
  id: number,
  instruction?: string,
  llm_model?: string
): Promise<{ new_html: string; new_seo_score: number; old_seo_score: number }> {
  const { data } = await api.post(`/articles/${id}/improve-preview`, { instruction, llm_model });
  return data;
}

export async function getSetting(key: string): Promise<{ key: string; value: string }> {
  const { data } = await api.get(`/settings/${key}`);
  return data;
}

export async function updateSetting(key: string, value: string): Promise<{ key: string; value: string }> {
  const { data } = await api.put(`/settings/${key}`, { value });
  return data;
}

export default api;
