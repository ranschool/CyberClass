# LearningSite

LearningSite הוא אתר לימודי סטטי עם עורך PySide6 מקומי. האתר מתפרסם ישירות מתיקיית `public/`; אין בו backend, חשבונות, analytics או מעקב התקדמות.

## התקנה והרצה

```powershell
python -m pip install -r requirements.txt
python main.py
```

להצגת האתר המקומי יש להגיש את `public/` באמצעות שרת סטטי:

```powershell
python -m http.server 8000 --directory public
```

## מבנה

```text
main.py                  # נקודת הכניסה לעורך
editor/content.py         # parsing, index, validation וקבצים
public/content/           # שיעורי Markdown
public/assets/images/     # תמונות
public/content-index.json # נבנה אוטומטית
public/search-index.json  # נבנה אוטומטית
public/.trash/            # סל מחזור מקומי, אינו מפורסם
```

## עמודים ו־metadata

קבצים ישנים ללא metadata ממשיכים לעבוד. עבור זהות יציבה וסדר מפורש אפשר להוסיף front matter:

```markdown
---
id: aes-introduction
title: הצפנת AES
order: 3
description: מבוא להצפנה סימטרית
tags:
  - cryptography
draft: false
---

# הצפנת AES
```

`draft: true` אינו מופיע באתר הציבורי. לכל תיקייה אפשר להוסיף `.folder.json`, לדוגמה `{"title":"סייבר","order":2,"description":"..."}`; קבצי metadata אינם הופכים לעמודים.

## Markdown נתמך

האתר משתמש ב־markdown-it. קיימת תמיכה בכותרות, רשימות, nested lists, קישורים, תמונות, טבלאות, ציטוטים, קוד inline ו־fenced code, Mermaid, RTL/LTR ו־callouts:

```markdown
:::warning
אזהרה חשובה
:::
```

סוגי callout: `note`, `tip`, `warning`, `danger`, `exercise`. בלוק `mermaid` נרנדר לתרשים. בלוקי קוד מקבלים highlighting, שם שפה וכפתור העתקה. קישורים ו־HTML עוברים sanitization.

## העורך

העורך בונה index ו־search index בכל שמירה. הוא מזהה שינויים שלא נשמרו, מגן על החלפה/סגירה/רענון, יוצר recovery מקומי, מונע דריסת שם של עמוד אחר, ומעביר מחיקות ל־`public/.trash`.

פעולת **בדיקת האתר** מדווחת על IDs/slugs כפולים, metadata בעייתי, תמונות חסרות או ללא שימוש, וקישורים לא בטוחים. ספריית התמונות מציגה היכן תמונה נמצאת בשימוש לפני מחיקה.

קיצורים: `Ctrl+S` שמירה, `Ctrl+N` עמוד חדש, `Ctrl+B` מודגש, `Ctrl+I` נטוי, `Ctrl+K` קישור, `Ctrl+P` preview, `Ctrl+F` מיקוד בעץ העמודים.

## אתר ופרסום

האתר כולל חיפוש מקומי (title/content/tags/description), תוכן עניינים, breadcrumbs, previous/next, 404 בטוח, ניווט מקלדת, מצב בהיר/כהה וממשק רספונסיבי. הוא גם PWA בסיסי עם service worker בעל cache versioning. ה־dependencies החיצוניות ב־CDN נעולות לגרסאות מדויקות.

ל־Cloudflare Pages הגדירו את `public` בתור Root directory, ללא build command. לאחר עריכה: `git add .`, `git commit -m "Update content"`, `git push`.
