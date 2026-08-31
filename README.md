# LearningSite — אתר סטטי + עורך תוכן

LearningSite היא מערכת ליצירה וניהול של אתר לימודי סטטי באמצעות עורך תוכן מקומי.

הפרויקט מחולק לשני אזורים:

```text
Learning site/
├── main.py              # תוכנת עריכת העמודים
├── requirements.txt     # תלות העורך בלבד
└── public/              # זהו האתר הסטטי שמועלה ל-Cloudflare Pages
    ├── index.html
    ├── assets/
    ├── content/         # כל שיעור הוא קובץ Markdown
    └── content-index.json
```

העורך המקומי משנה את תוכן האתר שבתיקייה `public/`.

כל משתמש יכול ליצור עותק משלו של LearningSite ב-GitHub, להוסיף אליו את התוכן שלו ולפרסם את תיקיית `public/` כאתר עצמאי.

---

## יצירת אתר משלכם באמצעות הפרויקט

הדרך המומלצת להשתמש ב-LearningSite היא ליצור **Fork** של ה-Repository.

כך לכל משתמש יש Repository עצמאי משלו:

```text
LearningSite המקורי
        │
        │ Fork
        ▼
Repository משלכם
        │
        ├── העורך
        ├── התוכן שלכם
        └── public/
              │
              ▼
        Cloudflare Pages
```

ה-Repository שלכם יכיל עותק מלא של LearningSite, אבל השיעורים, התמונות והגדרות האתר שתיצרו יהיו שייכים לאתר שלכם.

### 1. יצירת Fork

בעמוד ה-GitHub של LearningSite לחצו על:

**Fork**

GitHub ייצור בחשבון שלכם Repository חדש המבוסס על הפרויקט.

לדוגמה:

```text
הפרויקט המקורי:

github.com/ORIGINAL-OWNER/LearningSite

העותק שלכם:

github.com/YOUR-USERNAME/LearningSite
```

אפשר גם לתת ל-Repository שלכם שם אחר שמתאים לאתר.

לדוגמה:

```text
MyLearningSite
CyberCourse
NetworkingCourse
```

---

### 2. הורדת האתר למחשב

לאחר יצירת ה-Fork, העתיקו את כתובת ה-Repository שלכם ובצעו:

```powershell
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
```

עברו לתיקייה:

```powershell
cd YOUR-REPOSITORY
```

חשוב לעבוד על ה-Repository שלכם ולא לבצע Clone ישירות של ה-Repository המקורי אם אתם מתכוונים לשמור ולפרסם בו תוכן משלכם.

---

## הפעלת העורך

התקינו את התלות פעם אחת:

```powershell
python -m pip install -r requirements.txt
```

ולאחר מכן הפעילו:

```powershell
python main.py
```

בתוכנה אפשר ליצור עמוד, לבחור את התיקייה שלו, לקבוע את **סדר התצוגה** שלו, לערוך Markdown בסרגל עיצוב ולשמור. מספר 1 מוצג ראשון; בעת שמירה העורך מעביר את העמוד למקום שבחרתם ומעדכן את יתר העמודים אוטומטית.

בכל שמירה `public/content-index.json` מתעדכן אוטומטית. אין לערוך אותו ידנית.

אפשר גם לגרור עמוד או תיקייה בתפריט הצדדי: שחרור מעל או מתחת לפריט אחר משנה את סדר התצוגה באתר. שחרור במרכז תיקייה מעביר אליה את הקובץ או התיקייה פיזית, ולכן גם כתובת העמוד באתר מתעדכנת.

העורך חוסם התנגשות שמות וניסיון להעביר תיקייה לתוך עצמה.

---

### נושאים ותתי־נושאים

בעורך בוחרים תיקייה קיימת בתפריט **„מיקום בתיקיות”**.

כדי ליצור תיקייה או תת־תיקייה, לוחצים על **„+ תיקייה”**, בוחרים תיקיית אב ומזינים שם אחד לתיקייה החדשה. אין צורך להקליד נתיבים ידנית.

לדוגמה, אפשר ליצור את המסלול הבא בשלושה צעדים:

`02-סייבר` ← `01-הצפנה` ← `סימטרית`

```text
02-סייבר/01-הצפנה/סימטרית
```

עבור קובץ בשם `AES.md` העורך יצור:

```text
public/content/02-סייבר/01-הצפנה/סימטרית/AES.md
```

האתר יציג בתפריט עץ נושאים נפתח:

```text
סייבר
└── הצפנה
    └── סימטרית
        └── AES
```

---

### כיוון טקסט באתר

בעורך אפשר לסמן טקסט (או להציב את הסמן בשורה) וללחוץ על **„באתר RTL”** או **„באתר LTR”**.

העורך עוטף את הטקסט בהוראת Markdown מתאימה, והאתר מציג את האזור בכיוון וביישור שנבחרו.

---

### תמונות

בעורך לחצו על **„תמונה”** כדי לפתוח את ספריית התמונות.

אפשר לבחור תמונה קיימת מתוך:

```text
public/assets/images/
```

או להוסיף קובץ חדש לספרייה ולתת לו תיאור חלופי.

העורך מוסיף את תחביר ה-Markdown המתאים לעמוד.

---

### תרשימי Mermaid

לחצו על **„Mermaid”** בעורך כדי להוסיף תבנית תרשים. אפשר לערוך אותה באמצעות תחביר Mermaid; האתר ממיר כל בלוק שמתחיל ב־` ```mermaid ` לתרשים בעת הצגת העמוד. התרשימים נטענים דרך Mermaid CDN.

---

## שמירת האתר ב-GitHub

לאחר שיצרתם או ערכתם תוכן בעורך, השינויים נמצאים בתוך ה-Repository המקומי שלכם.

לדוגמה, שיעורים חדשים יישמרו בתוך:

```text
public/content/
```

תמונות שהוספתם יישמרו בתוך:

```text
public/assets/images/
```

ו-`content-index.json` יתעדכן אוטומטית.

כדי לשמור את השינויים ב-GitHub:

```powershell
git add .
git commit -m "Update site content"
git push
```

לאחר ה-`push`, הקבצים החדשים נמצאים ב-Repository שלכם.

אין למחוק או להוסיף ל-`.gitignore` את קובצי ה-Markdown של האתר שלכם — הם התוכן שהאתר מציג.

---

## פרסום ב-Cloudflare Pages

חברו את **ה-Repository שלכם** ל-Cloudflare Pages.

הגדירו את **Root directory** כ-`public`, ואז:

* **Framework preset:** `None`
* **Build command:** ריק
* **Build output directory:** `.`

רק התיקייה `public/` מתפרסמת.

תוכנת העורך וקובצי Python אינם עולים לאתר.

הזרימה היא:

```text
LearningSite Editor
        │
        │ יצירה / עריכה
        ▼
     public/
        │
        │ git push
        ▼
      GitHub
        │
        ▼
Cloudflare Pages
        │
        ▼
     האתר שלכם
```

לאחר שחיברתם את ה-Repository ל-Cloudflare Pages, עדכון האתר פשוט מתבצע על ידי עריכת התוכן ודחיפת השינויים ל-GitHub.

---

# קבלת עדכונים מ-LearningSite

אחד היתרונות בשימוש ב-Fork הוא שאפשר להמשיך לעבוד על האתר שלכם ובמקביל לקבל בעתיד תיקונים ושיפורים מהפרויקט המקורי.

לדוגמה, ייתכן שגרסה חדשה של LearningSite תכלול:

```text
main.py                  ← שיפורים בעורך
public/index.html        ← שיפורים באתר
public/assets/app.js     ← פונקציונליות חדשה
public/assets/styles.css ← שיפורי עיצוב
```

התוכן שאתם יצרתם נשאר ב-Repository שלכם:

```text
public/content/
public/assets/images/
```

---

## חיבור ה-Repository המקורי כ-Upstream

לאחר שביצעתם Clone ל-Fork שלכם, אפשר לחבר גם את הפרויקט המקורי.

בצעו פעם אחת:

```powershell
git remote add upstream https://github.com/ORIGINAL-OWNER/LearningSite.git
```

החליפו את הכתובת בכתובת האמיתית של ה-Repository המקורי.

אפשר לבדוק את החיבורים באמצעות:

```powershell
git remote -v
```

אמורים להופיע שני חיבורים:

```text
origin    → ה-Repository שלכם
upstream  → LearningSite המקורי
```

כלומר:

```text
origin
  │
  └── האתר שלכם

upstream
  │
  └── LearningSite המקורי
```

---

## קבלת גרסה חדשה של LearningSite

כאשר מתפרסם עדכון בפרויקט המקורי, משכו אותו באמצעות:

```powershell
git fetch upstream
```

ולאחר מכן מזגו את הגרסה החדשה לענף שלכם:

```powershell
git merge upstream/main
```

אם המיזוג הסתיים בהצלחה, העלו את השינויים ל-Repository שלכם:

```powershell
git push origin main
```

כעת האתר שלכם מכיל גם את התוכן שלכם וגם את הגרסה המעודכנת של LearningSite.

הזרימה היא:

```text
LearningSite המקורי
        │
        │ עדכון
        ▼
git fetch upstream
        │
        ▼
git merge upstream/main
        │
        ▼
ה-Repository שלכם
        │
        │ git push
        ▼
     GitHub
        │
        ▼
Cloudflare Pages
```

---

## מה שייך לפרויקט ומה שייך לאתר שלכם?

באופן כללי, קובצי המערכת מתעדכנים על ידי LearningSite:

```text
main.py
requirements.txt
public/index.html
public/assets/app.js
public/assets/styles.css
```

לעומת זאת, התוכן שנוצר באמצעות העורך שייך לאתר שלכם:

```text
public/content/
public/assets/images/
public/site-texts.json
public/content-index.json
```

`public/content-index.json` נוצר ומתעדכן אוטומטית על ידי העורך, אבל הוא עדיין צריך להישמר ב-GitHub מכיוון שהאתר משתמש בו.

---

## במקרה של Merge Conflict

Git בדרך כלל מסוגל לשלב את העדכונים באופן אוטומטי.

אם גם אתם וגם הפרויקט המקורי שיניתם את אותו קובץ או את אותן שורות, Git עשוי לדווח על `merge conflict`.

במקרה כזה יש לבדוק את הקובץ שבו נוצרה ההתנגשות, לבחור אילו שינויים לשמור, ולאחר מכן לבצע Commit.

ככלל, LearningSite משתדל להפריד בין קובצי המערכת לבין התוכן האישי של האתר, ולכן עבודה רגילה בתוך:

```text
public/content/
```

לא אמורה להתנגש עם רוב עדכוני המערכת.

---

# סיכום

כדי ליצור אתר משלכם באמצעות LearningSite:

```text
1. Fork ל-LearningSite
        ↓
2. Clone של ה-Fork למחשב
        ↓
3. התקנת requirements.txt
        ↓
4. הפעלת העורך
        ↓
5. יצירת שיעורים ותוכן
        ↓
6. git add / commit / push
        ↓
7. חיבור ה-Repository ל-Cloudflare Pages
        ↓
8. האתר באוויר
```

ובהמשך, כדי לקבל עדכונים מ-LearningSite:

```text
git fetch upstream
git merge upstream/main
git push origin main
```

כך לכל משתמש יש אתר עצמאי משלו, תוכן עצמאי ו-Repository משלו, אבל הוא עדיין יכול ליהנות מתיקונים ושיפורים שמתפרסמים בפרויקט LearningSite המקורי.
