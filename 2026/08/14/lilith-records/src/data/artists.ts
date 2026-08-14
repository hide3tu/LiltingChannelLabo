export interface Artist {
  slug: string;
  name: string;
  nameJa: string;
  role: string;
  description: string;
  image: string;
  features: string[];
}

export const artists: Artist[] = [
  {
    slug: 'kei',
    name: 'Kei',
    nameJa: 'ケイ',
    role: 'Vocal',
    description: 'Lilith-4のセンター。透明感のあるハイトーンボイスが特徴。',
    image: '/images/artists/kei.jpg',
    features: [
      '金髪ロング',
      '青目',
      'ぱっつん前髪',
      '長いインテーク',
      'ハーフアップ三つ編み',
      '青リボン',
    ],
  },
  {
    slug: 'kana',
    name: 'Kana',
    nameJa: 'カナ',
    role: 'Vocal / Dance',
    description: 'パワフルなダンスパフォーマンスと安定したボーカル。',
    image: '/images/artists/kana.jpg',
    features: [
      '茶髪ミディアム',
      'サイドポニテ',
      'アホ毛',
      '二重に分かれた前髪',
      '青シュシュ',
    ],
  },
  {
    slug: 'koharu',
    name: 'Koharu',
    nameJa: 'コハル',
    role: 'Vocal / Rap',
    description: 'クールな印象とは裏腹に、ステージではエネルギッシュ。',
    image: '/images/artists/koharu.jpg',
    features: [
      'ショートで乱れた黒髪',
      '青リボン',
      '赤目',
    ],
  },
  {
    slug: 'kurara',
    name: 'Kurara',
    nameJa: 'クララ',
    role: 'Vocal / Visual',
    description: 'グループのビジュアル担当。ギャル系のファッションが特徴。',
    image: '/images/artists/kurara.jpg',
    features: [
      'ローズブラウンのロングヘア',
      'センターパート',
      'スタッドピアス',
      'ライトギャルメイク',
    ],
  },
];

export function getArtistBySlug(slug: string): Artist | undefined {
  return artists.find((a) => a.slug === slug);
}
