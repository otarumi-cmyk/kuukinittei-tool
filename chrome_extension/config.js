// 設定（変更時はここを編集してチームに再配布）
export const EMAILS = [
  "y.hiraga@migi-nanameue.co.jp",
  "kotaro.suzuki@migi-nanameue.co.jp",
  "d.yokoyama@migi-nanameue.co.jp",
  "m.inoue@migi-nanameue.co.jp",
];

export const DISPLAY_NAMES = {
  "y.hiraga@migi-nanameue.co.jp": "平賀",
  "kotaro.suzuki@migi-nanameue.co.jp": "鈴木",
  "d.yokoyama@migi-nanameue.co.jp": "横山",
  "m.inoue@migi-nanameue.co.jp": "愛海",
};

// 空き日程ジェネレータ用: 最低何分以上の空きを採用するか
export const MIN_SLOT_MINUTES = {
  "y.hiraga@migi-nanameue.co.jp": 90,
  "kotaro.suzuki@migi-nanameue.co.jp": 90,
  "d.yokoyama@migi-nanameue.co.jp": 60,
  "m.inoue@migi-nanameue.co.jp": 60,
};

// Booking 用: 面談1コマの時間（分）
export const BOOKING_DURATION = {
  "y.hiraga@migi-nanameue.co.jp": 90,
  "kotaro.suzuki@migi-nanameue.co.jp": 90,
  "d.yokoyama@migi-nanameue.co.jp": 60,
  "m.inoue@migi-nanameue.co.jp": 60,
};

// 営業時間帯（曜日: 0=月, 6=日）
export const BOOKABLE_HOURS = {
  "y.hiraga@migi-nanameue.co.jp": { start: 10, end: 22, weekdays: [0,1,2,3,4,5,6] },
  "kotaro.suzuki@migi-nanameue.co.jp": { start: 10, end: 22, weekdays: [0,1,2,3,4,5,6] },
  "d.yokoyama@migi-nanameue.co.jp": { start: 10, end: 22, weekdays: [0,1,2,3,4,5,6] },
  "m.inoue@migi-nanameue.co.jp": { start: 10, end: 22, weekdays: [0,1,2,3,4,5,6] },
};

export const DEFAULT_MEETING_TITLE = "初回面談";

// Booking 時に自動で空きを探してアサインするフォンブース
export const PHONE_BOX_RESOURCES = [
  "c_1881pr03kdt28g58ncn5mq2g2mch6@resource.calendar.google.com",
  "c_188e8la9c1huejb8l65e8env61j08@resource.calendar.google.com",
  "c_188468t6mf1raib0h2dvksel4k0pe@resource.calendar.google.com",
  "c_1889bk6nq2veshmkieduuv9ta76n8@resource.calendar.google.com",
  "c_1889u9g33evpkjafldgjlhc80pp0u@resource.calendar.google.com",
  "c_188d4pcs4v7tqhephrchcbmt155uk@resource.calendar.google.com",
  "c_1881fa69dbjn4je0g6hm9s5k4n5uk@resource.calendar.google.com",
  "c_1881fbkj3nt8oh3dg67oi0l1hplmq@resource.calendar.google.com",
  "c_1884tlds0t7eehujnnu0limapch04@resource.calendar.google.com",
];
export const PHONE_BOX_NAMES = {
  "c_1881pr03kdt28g58ncn5mq2g2mch6@resource.calendar.google.com": "5F-A",
  "c_188e8la9c1huejb8l65e8env61j08@resource.calendar.google.com": "5F-B",
  "c_188468t6mf1raib0h2dvksel4k0pe@resource.calendar.google.com": "5F-C",
  "c_1889bk6nq2veshmkieduuv9ta76n8@resource.calendar.google.com": "5F-D",
  "c_1889u9g33evpkjafldgjlhc80pp0u@resource.calendar.google.com": "5F-E",
  "c_188d4pcs4v7tqhephrchcbmt155uk@resource.calendar.google.com": "5F-F",
  "c_1881fa69dbjn4je0g6hm9s5k4n5uk@resource.calendar.google.com": "3F-G",
  "c_1881fbkj3nt8oh3dg67oi0l1hplmq@resource.calendar.google.com": "3F-H",
  "c_1884tlds0t7eehujnnu0limapch04@resource.calendar.google.com": "3F-I",
};

// Booking時に通知用オプショナルゲストとして招待されるメアド
export const NOTIFY_EMAILS = [
  "k.suzuki@migi-nanameue.co.jp",
  "h.senda@migi-nanameue.co.jp",
];

export const TZ = "Asia/Tokyo";
export const WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"];
