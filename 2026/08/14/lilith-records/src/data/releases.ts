export interface Track {
  title: string;
  duration: string;
}

export interface Release {
  slug: string;
  title: string;
  type: 'single' | 'album' | 'mini-album';
  artist: string;
  releaseDate: string;
  catalogNumber: string;
  coverImage: string;
  tracks: Track[];
  links: {
    spotify?: string;
    youtube?: string;
    appleMusic?: string;
  };
}

export const releases: Release[] = [
  // Solo Singles
  {
    slug: 'kei-solo-single',
    title: 'Blue Ribbon',
    type: 'single',
    artist: 'Kei',
    releaseDate: '2026-05-01',
    catalogNumber: 'LILITH-S01',
    coverImage: '/images/artists/kei.jpg',
    tracks: [
      { title: 'Blue Ribbon', duration: '4:12' },
      { title: 'Blue Ribbon (Instrumental)', duration: '4:12' },
    ],
    links: {
      spotify: 'https://open.spotify.com/track/kei-solo',
      youtube: 'https://youtube.com/watch?v=kei-solo',
      appleMusic: 'https://music.apple.com/album/kei-solo',
    },
  },
  {
    slug: 'kana-solo-single',
    title: 'Side Ponytail',
    type: 'single',
    artist: 'Kana',
    releaseDate: '2026-05-15',
    catalogNumber: 'LILITH-S02',
    coverImage: '/images/artists/kana.jpg',
    tracks: [
      { title: 'Side Ponytail', duration: '3:45' },
      { title: 'Side Ponytail (Instrumental)', duration: '3:45' },
    ],
    links: {
      spotify: 'https://open.spotify.com/track/kana-solo',
      youtube: 'https://youtube.com/watch?v=kana-solo',
      appleMusic: 'https://music.apple.com/album/kana-solo',
    },
  },
  {
    slug: 'koharu-solo-single',
    title: 'Red Eyes',
    type: 'single',
    artist: 'Koharu',
    releaseDate: '2026-06-01',
    catalogNumber: 'LILITH-S03',
    coverImage: '/images/artists/koharu.jpg',
    tracks: [
      { title: 'Red Eyes', duration: '3:58' },
      { title: 'Red Eyes (Instrumental)', duration: '3:58' },
    ],
    links: {
      spotify: 'https://open.spotify.com/track/koharu-solo',
      youtube: 'https://youtube.com/watch?v=koharu-solo',
      appleMusic: 'https://music.apple.com/album/koharu-solo',
    },
  },
  {
    slug: 'kurara-solo-single',
    title: 'Gal Makeup',
    type: 'single',
    artist: 'Kurara',
    releaseDate: '2026-06-15',
    catalogNumber: 'LILITH-S04',
    coverImage: '/images/artists/kurara.jpg',
    tracks: [
      { title: 'Gal Makeup', duration: '4:23' },
      { title: 'Gal Makeup (Instrumental)', duration: '4:23' },
    ],
    links: {
      spotify: 'https://open.spotify.com/track/kurara-solo',
      youtube: 'https://youtube.com/watch?v=kurara-solo',
      appleMusic: 'https://music.apple.com/album/kurara-solo',
    },
  },
  // Group Releases
  {
    slug: 'debut-single',
    title: 'Lilith-4',
    type: 'single',
    artist: 'Lilith-4',
    releaseDate: '2026-04-01',
    catalogNumber: 'LILITH-001',
    coverImage: '/logo.svg',
    tracks: [
      { title: 'Lilith-4', duration: '4:23' },
      { title: 'Midnight Protocol', duration: '3:45' },
      { title: 'Lilith-4 (Instrumental)', duration: '4:23' },
    ],
    links: {
      spotify: 'https://open.spotify.com/track/example1',
      youtube: 'https://youtube.com/watch?v=example1',
      appleMusic: 'https://music.apple.com/album/example1',
    },
  },
  {
    slug: 'first-album',
    title: 'AWAKENING',
    type: 'album',
    artist: 'Lilith-4',
    releaseDate: '2026-07-15',
    catalogNumber: 'LILITH-002',
    coverImage: '/images/releases/awakening.jpg',
    tracks: [
      { title: 'Prologue', duration: '1:30' },
      { title: 'AWAKENING', duration: '4:56' },
      { title: 'Digital Dreams', duration: '3:42' },
      { title: 'Neon Tears', duration: '4:11' },
      { title: 'Cyber Heart', duration: '3:58' },
      { title: 'Binary Star', duration: '4:33' },
      { title: 'Phantom', duration: '3:27' },
      { title: 'Epilogue', duration: '2:15' },
    ],
    links: {
      spotify: 'https://open.spotify.com/album/example2',
      youtube: 'https://youtube.com/watch?v=example2',
      appleMusic: 'https://music.apple.com/album/example2',
    },
  },
];

export function getReleaseBySlug(slug: string): Release | undefined {
  return releases.find((r) => r.slug === slug);
}
