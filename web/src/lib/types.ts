export type Platform = 'youtube' | 'tiktok' | 'instagram' | 'link';
export type NativePlatform = 'youtube' | 'tiktok' | 'instagram';
export type LinkType = 'am' | 'xml' | 'other';
export type FileKind = 'xml' | 'zip' | 'sound' | 'folder' | 'video' | 'image' | 'apk' | 'file';

export interface LinkInfo {
  status?: 'ok' | 'dead' | 'error' | 'private';
  project_names?: string[] | null;
  name?: string | null;
  thumb?: string | null;
  size_mb?: number | null;
  size_text?: string | null;
  projects?: number | null;
  share_url?: string | null;
  fixed_url?: string;
  free_ok?: boolean;
}

export interface FoundLink {
  type: LinkType;
  url: string;
  source: string;
  by?: string | null;
  count: number;
  kind?: FileKind;
  info?: LinkInfo;
}

export interface VideoItem {
  platform: NativePlatform;
  id: string;
  url: string;
  title?: string | null;
  caption?: string;
  author?: string | null;
  author_handle?: string | null;
  author_url?: string | null;
  views?: number | null;
  likes?: number | null;
  duration?: number | null;
  ts?: number | null;
  thumb?: string | null;
  play?: string | null;
  vertical?: boolean;
  rank?: number;
}

export interface ScanResult extends VideoItem {
  links: FoundLink[];
  n_am: number;
  n_ok: number;
  n_xml: number;
  min_size: number | null;
  error?: string;
  bio_hint?: boolean;
  scanned_at?: number;
}

export interface Profile {
  handle: string;
  name?: string;
  bio?: string;
  avatar?: string;
  followers?: number | null;
  likes?: number | null;
  verified?: boolean;
  url: string;
  links?: FoundLink[];
}

export interface ListResponse {
  items: VideoItem[];
  profile: Profile | null;
  notes: string[];
  preset_check: FoundLink[] | null;
}

export interface Health {
  ok: boolean;
  version: string;
  serverless: boolean;
  hashtag_live: boolean;
  youtube_download: boolean;
  max_scan: number;
}

export interface FeedSource {
  platform: NativePlatform;
  id: string;
  video_url: string;
  title: string;
  author?: string | null;
  author_handle?: string | null;
  views?: number | null;
  source: string;
  xml: string[];
  via?: string;
  vertical?: boolean;
  thumb?: string | null;
}

export interface Preset {
  key: string;
  am_url: string;
  name?: string | null;
  size_mb?: number | null;
  size_text?: string | null;
  projects?: number | null;
  thumb?: string | null;
  first_seen?: number;
  last_seen?: number;
  saved_at?: number;
  sources: FeedSource[];
}

export interface Feed {
  updated: number | null;
  mode?: 'crawler' | 'live' | 'empty';
  tags?: string[];
  items: Preset[];
}

export interface PlayerTarget {
  platform: NativePlatform;
  id: string;
  title?: string | null;
  author?: string | null;
  url: string;
  vertical?: boolean;
  play?: string | null;
  thumb?: string | null;
}
