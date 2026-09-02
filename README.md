# LearningSite

LearningSite הוא אתר לימודי סטטי בעברית עם עורך תוכן מקומי מבוסס PySide6. האתר עצמו מוגש ישירות מתיקיית `public/`; אין בו backend, חשבונות או מסד נתונים.

## התקנה והרצה

```powershell
python -m pip install -r requirements.txt
python main.py
```

העורך כולל כפתור **תצוגת אתר** שמפעיל שרת סטטי מקומי ופותח את האתר בדפדפן. אפשר גם להפעיל אותו ידנית:

```powershell
python -m http.server 8000 --directory public
```

## יצירת אתר משלכם: Fork, GitHub ו־Cloudflare Pages

הדרך המומלצת היא ליצור **Fork** של [ה־repository המקורי של LearningSite](https://github.com/galtauba/LearningSite). כך קובצי המערכת יכולים לקבל עדכונים מהפרויקט, בעוד שהתוכן והגדרות האתר נמצאים ב־repository משלכם.

```text
LearningSite המקורי
        │ Fork
        ▼
ה־repository שלכם
        │ git push
        ▼
Cloudflare Pages → האתר שלכם
```

### 1. יצירת Fork והורדה למחשב

בעמוד [LearningSite ב־GitHub](https://github.com/galtauba/LearningSite) לחצו על **Fork**. לאחר מכן העתיקו את כתובת ה־repository החדש שלכם והריצו:

```powershell
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
python -m pip install -r requirements.txt
python main.py
```

החליפו את `YOUR-USERNAME` ואת `YOUR-REPOSITORY` בפרטים שלכם. חשוב לבצע clone של ה־Fork שלכם, כדי שכל התוכן והפרסום יתבצעו תחת החשבון שלכם.

### 2. שמירת עדכונים ב־repository שלכם

לאחר יצירה או עריכה של תוכן, הגדרות או קוד, בדקו את השינויים ושמרו אותם ב־GitHub:

```powershell
git status
git add .
git commit -m "Update site content"
git push origin main
```

אם הענף הראשי אצלכם נקרא אחרת, החליפו את `main` בשם הענף. אפשר גם להשתמש בהודעת commit שמתארת את העדכון, למשל `Add Python lesson` או `Update homepage settings`.

### 3. פרסום ב־Cloudflare Pages

ב־Cloudflare Pages חברו את **ה־repository שלכם** והגדירו:

- **Framework preset:** `None`
- **Root directory:** `public`
- **Build command:** ריק
- **Build output directory:** `.`

רק תיקיית `public/` מתפרסמת לאתר. העורך, Python וקובצי הפיתוח נשארים ב־repository אך אינם מוגשים לדפדפן. לאחר כל `git push` ל־branch המחובר, Cloudflare Pages בונה ומפרסם את הגרסה המעודכנת.

### 4. קבלת עדכונים מהפרויקט המקורי

כדי לקבל בעתיד תיקונים ושיפורים ל־LearningSite, חברו פעם אחת את ה־repository המקורי כ־`upstream`:

```powershell
git remote add upstream https://github.com/galtauba/LearningSite.git
git remote -v
```

כאשר יש עדכון בפרויקט המקורי, משכו אותו ומזגו אותו ל־Fork שלכם:

```powershell
git fetch upstream
git merge upstream/main
git push origin main
```

החליפו את כתובת ה־`upstream` ואת שם הענף אם הפרויקט המקורי משתמש בשמות אחרים. אם Git מדווח על `merge conflict`, פותרים את ההתנגשות בקבצים הרלוונטיים, מבצעים `git add .`, ואז `git commit` ו־`git push`.

## מבנה הפרויקט

```text
main.py                    # יישום העורך ונקודת הכניסה
editor/content.py           # אינדקס, חיפוש, ולידציה ותמונות
public/index.html           # מעטפת האתר
public/assets/              # JavaScript, CSS, אייקון וספריות מקומיות
public/content/             # שיעורי Markdown ותיקיות תוכן
public/assets/images/       # תמונות לשיעורים
public/content-index.json   # אינדקס עמודים שנבנה על ידי העורך
public/search-index.json    # אינדקס חיפוש שנבנה על ידי העורך
public/site-texts.json      # טקסטים וגדלי תצוגה של האתר
public/homepage.json        # הגדרות עמוד הבית האופציונלי
public/manifest.webmanifest # הגדרות PWA שנוצרות ומעודכנות על ידי העורך
public/.trash/              # סל מחזור מקומי, לא מפורסם
```

## ניהול תוכן

כל שיעור הוא קובץ Markdown תחת `public/content/`. העורך מנהל את הכותרת, מיקום התיקייה, שם הקובץ, סדר התצוגה ומצב הפרסום. `content-index.json` הוא מקור האמת לרשימת העמודים המפורסמים ולסדר שלהם; עמוד שאינו מפורסם אינו נכנס לאינדקס ואינו מוצג באתר.

העורך בונה מחדש את אינדקס העמודים ואת אינדקס החיפוש בכל שמירה, שינוי שם, העברת תיקייה, מחיקה או שינוי פרסום. מחיקות מועברות אל `public/.trash/` כדי לאפשר שחזור ידני.

## Markdown נתמך

האתר משתמש ב־markdown-it עם ספריות מקומיות ל־DOMPurify, Highlight.js ו־Mermaid. יש תמיכה בכותרות, רשימות, קישורים, תמונות, טבלאות, ציטוטים, קוד inline, בלוקי קוד, Mermaid ובלוקי RTL/LTR.

לדוגמה, callout:

```markdown
:::warning
אזהרה חשובה
:::
```

סוגי callout: `note`, `tip`, `warning`, `danger`, `exercise`. בלוק `mermaid` נרנדר לתרשים; בלוקי קוד מקבלים highlighting וכפתור העתקה. Markdown עובר sanitization, וקישורים וכתובות תמונה לא בטוחות נחסמים.

## העורך

הממשק כולל:

- עץ תוכן עם יצירת עמודים ותיקיות, פרסום/הסרה מפרסום, שינוי סדר, שינוי שם ומחיקה.
- כפתורי **פתח הכול** ו־**סגור הכול** לעץ התיקיות.
- אזור **פרטי העמוד** מעל העורך, שאפשר לקפל ולפתוח כדי לפנות גובה לכתיבה.
- כלי כתיבה עבור כותרות, מודגש, נטוי, רשימות, קישורים, תמונות, כיוון RTL/LTR, Mermaid וקוד.
- ספריית תמונות שמראה היכן תמונה נמצאת בשימוש לפני מחיקה.
- שמירת טיוטת recovery מקומית והגנה מפני מעבר או סגירה עם שינויים שלא נשמרו.
- שינוי גודל טקסט לכל ממשק העורך.
- הגדרות אתר עבור מותג, טקסטים קבועים, גדלי פונטים, ניווט וטקסטי עמוד הבית.
- הגדרת עמוד בית, החלפת סמל אתר ובדיקת תוכן.

קיצורים: `Ctrl+S` שמירה, `Ctrl+N` עמוד חדש, `Ctrl+B` מודגש, `Ctrl+I` נטוי, `Ctrl+K` קישור, `Ctrl+P` פתיחה או עצירה של האתר המקומי, `Ctrl+F` מיקוד בעץ העמודים.

### הגדרות האתר ו־PWA

דרך **הגדרות אתר** אפשר לשנות את כותרת האתר, שם המותג, תיאור, טקסטי ניווט, גדלי פונטים וטקסטים קבועים בעמוד הבית — כולל כפתור ההתחלה, כותרות קטגוריות ומומלצים, ונוסח מונה העמודים (`{count}`).

בעת פתיחת העורך ובכל שמירה של הגדרות האתר, `manifest.webmanifest` נוצר או מתעדכן אוטומטית לפי ההגדרות: שם האתר, השם הקצר, התיאור, עברית ו־RTL. האייקון הנוכחי תחת `public/assets/favicon.*` מתווסף גם ל־manifest. החלפת סמל האתר בעורך מעדכנת את HTML ואת ה־manifest.

### עמוד בית אופציונלי

בתפריט **הגדרות אתר** בחרו **עמוד הבית** כדי להפעיל מסך פתיחה. אפשר להגדיר כותרת, תיאור, עמוד התחלה, קטגוריות, מוני עמודים ועמודים מומלצים. ההגדרות נשמרות ב־`public/homepage.json`; כאשר המסך כבוי או הקובץ חסר, הנתיב הראשי פותח את העמוד הראשון המפורסם.

## האתר ופרסום

האתר כולל חיפוש מקומי בתוכן ובכותרות, ניווט היררכי, תוכן עניינים, breadcrumbs, previous/next, מצב בהיר/כהה, 404 בטוח, קיצורי מקלדת, רספונסיביות ו־PWA בסיסי עם service worker ו־cache versioning.

ל־Cloudflare Pages הגדירו את `public` בתור Root directory וללא build command.
