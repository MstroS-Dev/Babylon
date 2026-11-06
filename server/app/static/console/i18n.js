/* Babylon console — Hebrew (RTL) support.
 *
 * English is the source language of the console. When the language is Hebrew this file translates
 * every piece of visible text (text nodes, title/placeholder attributes) as it appears in the page,
 * so the rest of the code stays in plain English and English mode is untouched.
 *
 * To translate a new string: add it to HE (exact text) or HE_RULES (text with numbers / names in it).
 * Anything not listed simply stays in English.
 */
(function(){
  'use strict';
  var LANG = 'en';
  try{
    LANG = localStorage.getItem('babylon_lang') || ((navigator.language || '').toLowerCase().indexOf('he') === 0 ? 'he' : 'en');
  }catch(_){}
  window.LANG = LANG;
  window.setLang = function(l){ try{ localStorage.setItem('babylon_lang', l); }catch(_){} location.reload(); };

  var HE = {
    // top bar / crew
    'Site Console':'לוח בקרה לאתר', 'connecting…':'מתחבר…', 'live':'מחובר', 'reconnecting…':'מתחבר מחדש…',
    'Roster':'צוות', 'Crew':'עובדים',
    'Drag a worker onto the building to pin their next task. Tap + for a task with no fixed location.':'גררו עובד אל הבניין כדי לנעוץ את המשימה הבאה שלו. לחצו על + למשימה ללא מיקום קבוע.',
    'No workers registered yet.':'עדיין לא נרשמו עובדים.',
    'No one with that trade here.':'אין כאן עובדים במקצוע הזה.',
    'Drag to orbit · Scroll to zoom ·':'גררו כדי לסובב · גלגלת לזום ·',
    'Drop a worker on a floor to place a task':'שחררו עובד על קומה כדי למקם משימה',
    'Switch theme':'החלפת ערכת נושא', 'Show only one trade':'הצגת מקצוע אחד בלבד', 'All trades':'כל המקצועות',
    '+ trade':'+ מקצוע', "Set this worker's trade (only you can)":'קביעת המקצוע של העובד (רק אתם יכולים)',
    'Assign task without a location':'שיבוץ משימה ללא מיקום', 'Remove worker':'הסרת עובד',
    'On shift':'במשמרת', 'Off shift':'מחוץ למשמרת',
    'Unassigned':'לא משויך', 'Unassigned — not in any building yet':'לא משויכים — עדיין לא בבניין',
    'Which building this worker belongs to (one at a time)':'לאיזה בניין העובד שייך (אחד בכל פעם)',
    // stage buttons / floors
    'Steps':'שלבים', 'Floor':'קומה', 'Add':'הוספה', 'Add floor':'הוספת קומה', 'Isolate floor':'בידוד קומה',
    'Import floor plan':'ייבוא תוכנית קומה', 'Ground':'קרקע', 'Roof':'גג',
    'Building steps: a checklist for each floor':'שלבי בנייה: רשימת משימות לכל קומה',
    'Add a step…':'הוספת שלב…', 'Add the standard steps':'הוספת השלבים הסטנדרטיים', 'No steps yet':'עדיין אין שלבים',
    'Remove step':'הסרת שלב',
    'Structure':'שלד', 'Walls':'קירות', 'Electrical':'חשמל', 'Plumbing':'אינסטלציה', 'Plaster':'טיח',
    'Flooring':'ריצוף', 'Painting':'צבע', 'Final inspection':'בדיקה סופית',
    'Show only the selected floor (floors above hidden, floors below faded)':'הצגת הקומה הנבחרת בלבד (קומות מעליה מוסתרות, מתחתיה עמומות)',
    'Import a floor plan from CAD (DWG, DXF or vector PDF)':'ייבוא תוכנית קומה מ-CAD‏ (DWG, DXF או PDF וקטורי)',
    'Segments':'קטעים', 'Whole wall':'קיר שלם',
    'Click one segment, Ctrl/Cmd-drag for a range':'לחיצה על קטע אחד, ‏Ctrl/Cmd וגרירה לטווח',
    'Click a wall to select all of it':'לחצו על קיר כדי לבחור את כולו',
    'Click a wall to mark the workspace':'לחצו על קיר כדי לסמן את אזור העבודה',
    'Click a segment · Ctrl/Cmd-drag for a range':'לחצו על קטע · ‏Ctrl/Cmd וגרירה לטווח',
    'Cancel':'ביטול', 'Done':'סיום', 'Close':'סגירה',
    'Move over a floor to place the task':'העבירו מעל קומה כדי למקם את המשימה',
    // buildings
    '+ Building':'+ בניין', 'Create a new building':'יצירת בניין חדש', 'Double-click to rename':'לחיצה כפולה לשינוי שם',
    'Delete this building':'מחיקת הבניין', 'Buildings':'בניינים', 'New building':'בניין חדש', 'Name':'שם',
    'Number of floors':'מספר קומות', 'e.g. Tower B':'למשל: מגדל ב׳',
    'Add the standard steps checklist to every floor':'הוספת רשימת השלבים הסטנדרטית לכל קומה',
    'From a drawing? Choose “Create & import CAD”: if the file holds several floors side by side, they are split into floors automatically.':'מתוך שרטוט? בחרו ״יצירה וייבוא CAD״: אם בקובץ כמה קומות זו לצד זו, הן יפוצלו לקומות אוטומטית.',
    'Create & import CAD':'יצירה וייבוא CAD', 'Create':'יצירה', 'Building name':'שם הבניין',
    'Name this floor (e.g. "6" or "Roof")':'שם הקומה (למשל "6" או "גג")', 'That floor already exists':'הקומה כבר קיימת',
    // plan import
    'Floor plan':'תוכנית קומה', 'Import from CAD':'ייבוא מ-CAD',
    'Upload your CAD file (.dwg, .dxf or a vector .pdf exported from CAD).':'העלו קובץ CAD‏ (‎.dwg, ‎.dxf או ‎.pdf וקטורי שיוצא מ-CAD).',
    'Reading file…':'קורא את הקובץ…', 'Could not reach the server.':'אין חיבור לשרת.', 'No walls found.':'לא נמצאו קירות.',
    'Which':'אילו', 'layers':'שכבות', 'stroke style':'סגנונות קו', 'are the walls?':'הם הקירות?',
    'Drawing scale 1 :':'קנה מידה 1 :', 'Page':'עמוד', 'Units':'יחידות', 'Auto (from file)':'אוטומטי (מהקובץ)',
    'mm':'מ״מ', 'cm':'ס״מ', 'm':'מ׳', 'inches':'אינצ׳ים', 'feet':'רגל',
    'Merge double-line walls into one wall':'איחוד קירות דו-קוויים לקיר אחד',
    'Show doors, windows, stairs & furniture on the floor':'הצגת דלתות, חלונות, מדרגות וריהוט על הקומה',
    "This drawing is just ONE floor (don't split it)":'השרטוט הזה הוא קומה אחת בלבד (לא לפצל)',
    '— skip —':'— דילוג —', 'Use generic layout':'שימוש בפריסה כללית', 'Save floor plan':'שמירת תוכנית קומה',
    'Saving…':'שומר…', 'Save failed':'השמירה נכשלה', 'Pick a floor for at least one of the drawings.':'בחרו קומה לפחות לאחד השרטוטים.',
    'Could not reset the plan':'לא ניתן לאפס את התוכנית',
    'Unsupported file. Upload a .dwg, a .dxf or a vector .pdf exported from CAD.':'קובץ לא נתמך. העלו קובץ dwg‏, dxf או pdf וקטורי שיוצא מ-CAD.',
    'Pick at least one layer to build walls from.':'בחרו לפחות שכבה אחת שממנה ייבנו הקירות.',
    'The selected layers contain no lines.':'השכבות שנבחרו אינן מכילות קווים.',
    'No wall-length lines found on the selected layers.':'לא נמצאו קווים באורך של קיר בשכבות שנבחרו.',
    "This server can't read .dwg files yet (the converter isn't installed). Either up":'השרת עדיין לא יכול לקרוא קבצי dwg (הממיר אינו מותקן). ',
    'File too large (40 MB max)':'הקובץ גדול מדי (מקסימום 40MB)',
    // task modal
    'New task':'משימה חדשה', '—':'—', 'Title':'כותרת', 'Description':'תיאור',
    'e.g. Pour footing along column line B':'למשל: יציקת יסוד לאורך ציר העמודים B',
    'What needs to happen, materials, safety notes…':'מה צריך לקרות, חומרים, הערות בטיחות…',
    'Required proof photo':'תמונת הוכחה נדרשת', '(optional — AI checks every upload against this)':'(לא חובה — הבינה המלאכותית בודקת כל תמונה מולה)',
    'e.g. the cement blocks stacked by the north wall':'למשל: בלוקי הבטון שנערמו ליד הקיר הצפוני',
    'Location':'מיקום', 'Not required':'לא נדרש', 'anywhere on site':'בכל מקום באתר', 'Pinpoint':'נעיצה',
    'shown on their map':'מוצג במפה שלהם', 'GPS live':'GPS חי', 'tracked to the pin':'מעקב אחרי הנעץ',
    'Photo check-in':'אישור הגעה בתמונה', 'you approve on arrival':'אתם מאשרים בהגעה',
    'Workspace':'אזור עבודה', '(optional — mark the exact wall stretch)':'(לא חובה — סימון קטע הקיר המדויק)',
    'Mark workspace':'סימון אזור עבודה', 'Spot description':'תיאור המקום', '(optional, sent to worker)':'(לא חובה, נשלח לעובד)',
    'e.g. north stairwell, by the electrical panel':'למשל: חדר מדרגות צפוני, ליד לוח החשמל',
    'Create task':'יצירת משימה', 'Creating…':'יוצר…', 'Worker':'עובד',
    'Pin shown on their map':'נעץ מוצג במפה שלהם', 'Live GPS tracked to pin':'GPS חי מול הנעץ', 'Photo check-in required':'נדרש אישור הגעה בתמונה',
    'Title and description are required':'כותרת ותיאור הם שדות חובה', 'Failed to create task':'יצירת המשימה נכשלה',
    'Drag this worker onto the building first to set a location':'גררו קודם את העובד אל הבניין כדי לקבוע מיקום',
    'Task assigned':'המשימה שובצה',
    // task history panel / photos
    'No tasks yet.':'עדיין אין משימות.', 'Needs photo of':'נדרשת תמונה של',
    'assigned':'שובצה', 'in progress':'בביצוע', 'done':'הושלמה', 'sent':'נשלחה',
    'before':'לפני', 'after':'אחרי', 'Match':'תואם', 'No match':'לא תואם', 'Unclear':'לא ברור',
    'Admin: OK':'מנהל: תקין', 'Admin: Not OK':'מנהל: לא תקין', 'Mark OK':'סימון כתקין', 'Mark not OK':'סימון כלא תקין',
    'Marked as OK':'סומן כתקין', 'Marked as not OK':'סומן כלא תקין', 'Failed to update photo review':'עדכון בדיקת התמונה נכשל',
    'Current task':'משימה נוכחית', 'Nothing assigned right now':'אין משימה כרגע', 'Working now':'עובד כעת',
    'Sent · not started yet':'נשלחה · טרם התחילה',
    'Check-in photo submitted — review needed':'נשלחה תמונת הגעה — נדרש אישור',
    // WhatsApp worker
    'Add WhatsApp worker':'הוספת עובד וואטסאפ',
    "For workers who don't use the app — messages are sent straight to WhatsApp.":'לעובדים שלא משתמשים באפליקציה — ההודעות נשלחות ישירות לוואטסאפ.',
    'Phone number':'מספר טלפון', 'Language':'שפה', 'Full name':'שם מלא',
    'Hebrew':'עברית', 'English':'אנגלית', 'Arabic':'ערבית', 'Russian':'רוסית', 'Chinese':'סינית', 'Thai':'תאילנדית',
    'Uzbek':'אוזבקית', 'Sinhala':'סינהלית', 'Hindi':'הינדי',
    'Add worker':'הוספת עובד', 'Adding…':'מוסיף…', 'Name and phone are required':'שם וטלפון הם שדות חובה',
    'Could not add worker':'לא ניתן להוסיף עובד', 'Could not remove worker':'לא ניתן להסיר את העובד',
    'Could not save the trade':'לא ניתן לשמור את המקצוע',
    // server messages
    'Worker not found':'העובד לא נמצא', 'Task not found':'המשימה לא נמצאה', 'Building not found':'הבניין לא נמצא',
    'Give the building a name.':'תנו שם לבניין.', 'A building needs at least one floor.':'לבניין חייבת להיות לפחות קומה אחת.',
    "You can't delete the only building.":'אי אפשר למחוק את הבניין היחיד.',
    "That floor doesn't exist in this building.":'הקומה הזו לא קיימת בבניין.', 'Give the step a name.':'תנו שם לשלב.',
    'Step not found':'השלב לא נמצא', 'This floor already has steps.':'לקומה הזו כבר יש שלבים.', 'Request failed':'הבקשה נכשלה',
    'Switch to dark theme':'מעבר לערכת נושא כהה', 'Switch to light theme (better in direct sun)':'מעבר לערכת נושא בהירה (טובה יותר בשמש ישירה)',
    'Main building':'בניין ראשי', 'layer':'שכבות',
    // professions page + task brief
    'Professions':'מקצועות', 'Define professions and what each one is supposed to do':'הגדרת מקצועות ומה כל אחד אמור לעשות',
    'Back to the console':'חזרה ללוח הבקרה',
    'Define the trades on your site. For each one you can optionally write what that profession is supposed to be doing. The text appears when you assign a task to a worker of that profession (you can drop it into the task description), and it is given to the AI that checks their photos.':'הגדירו את המקצועות באתר. לכל מקצוע אפשר לכתוב, אם רוצים, מה בעל המקצוע אמור לעשות. הטקסט מופיע כשמשבצים משימה לעובד במקצוע הזה (אפשר להעתיק אותו לתיאור המשימה), והוא מועבר גם לבינה המלאכותית שבודקת את התמונות שלהם.',
    'New profession':'מקצוע חדש', 'Hebrew name (optional)':'שם בעברית (לא חובה)',
    'What are they supposed to be doing? (optional)':'מה הם אמורים לעשות? (לא חובה)',
    'e.g. Glazier':'למשל: Glazier',
    'e.g. Measures and installs window frames and glass, seals joints, checks that every window opens and closes. Works only after plastering is done.':'למשל: מודד ומתקין משקופי חלונות וזכוכית, אוטם חיבורים, בודק שכל חלון נפתח ונסגר. עובד רק אחרי שהטיח הסתיים.',
    'Add profession':'הוספת מקצוע', 'Save':'שמירה', 'Saved':'נשמר', 'Delete':'מחיקה',
    'No professions yet.':'עדיין אין מקצועות.', 'Profession added':'המקצוע נוסף',
    'Give the profession a name.':'תנו שם למקצוע.', 'A profession with this name already exists.':'מקצוע בשם הזה כבר קיים.',
    'Profession not found':'המקצוע לא נמצא',
    'Profession guidance':'הנחיות המקצוע', 'Use as description':'שימוש כתיאור',
    // multi-select of wall stretches
    'No profession':'ללא מקצוע', '+ New profession…':'+ מקצוע חדש…', 'New profession name':'שם המקצוע החדש',
    'Add more':'הוספה לבחירה',
    'Add to the selection instead of replacing it (same as holding Shift)':'הוספה לבחירה במקום החלפתה (כמו לחיצה על Shift)',
    'Click a segment · Ctrl/Cmd-drag for a range · Shift+click to add more':'לחצו על קטע · ‏Ctrl/Cmd וגרירה לטווח · ‏Shift ולחיצה להוספה',
    'Click a wall to select all of it · Shift+click to add more':'לחצו על קיר כדי לבחור את כולו · ‏Shift ולחיצה להוספת קירות',
    'Click one segment, Ctrl/Cmd-drag for a range, Shift+click to add more':'לחיצה על קטע אחד, ‏Ctrl/Cmd וגרירה לטווח, ‏Shift ולחיצה להוספה',
    'Click a wall to select all of it, Shift+click to add more walls':'לחצו על קיר כדי לבחור את כולו, ‏Shift ולחיצה להוספת קירות'
  };

  var NAMES = {north:'צפוני', south:'דרומי', east:'מזרחי', west:'מערבי'};
  var SIDE = {north:'צפון', south:'דרום', east:'מזרח', west:'מערב'};
  var WALLWORDS = {
    'north wall':'הקיר הצפוני', 'east wall':'הקיר המזרחי', 'south wall':'הקיר הדרומי', 'west wall':'הקיר המערבי',
    'interior partition (front-back)':'מחיצה פנימית (קדימה-אחורה)', 'interior partition (left-right)':'מחיצה פנימית (שמאל-ימין)'
  };
  var SECTION = {left:'שמאלי', middle:'אמצעי', right:'ימני'};
  var STATUS = {assigned:'שובצה', 'in progress':'בביצוע', in_progress:'בביצוע', done:'הושלמה', sent:'נשלחה'};

  // [regex, function(match) -> Hebrew]. Checked in order; first hit wins. "t" translates nested text.
  var LANGNAMES = {he:'עברית', en:'אנגלית', ar:'ערבית', ru:'רוסית', zh:'סינית', th:'תאילנדית', uz:'אוזבקית', si:'סינהלית', hi:'הינדי', ur:'אורדו', ro:'רומנית'};
  var CHANNELS = {app:'אפליקציה', whatsapp:'וואטסאפ'};
  var HE_RULES = [
    [/^([a-z]{2,3}) · (app|whatsapp) ·$/, function(m){ return (LANGNAMES[m[1]] || m[1]) + ' · ' + CHANNELS[m[2]] + ' ·'; }],
    [/^(🟢|⚪) (On|Off) shift$/, function(m){ return m[1] + ' ' + (m[2] === 'On' ? 'במשמרת' : 'מחוץ למשמרת'); }],
    [/^(.+) ✓$/, function(m, t){ return t(m[1]) + ' ✓'; }],
    [/^(\d+) workers?$/, function(m){ return m[1] + ' עובדים'; }],
    [/^(\d+) workers? · (\d+) unassigned$/, function(m){ return m[1] + ' עובדים · ' + m[2] + ' לא משויכים'; }],
    [/^(\d+) areas$/, function(m){ return m[1] + ' אזורים'; }],
    [/^(\d+) segments$/, function(m){ return m[1] + ' קטעים'; }],
    [/^Delete "(.+)"\?(?: (\d+) worker\(s\) will be left without a profession\.)?$/, function(m){
      return 'למחוק את "' + m[1] + '"?' + (m[2] ? ' ' + m[2] + ' עובדים יישארו בלי מקצוע.' : ''); }],
    [/^(\d+) tasks?$/, function(m){ return m[1] + ' משימות'; }],
    [/^No workers in (.+) yet\.$/, function(m){ return 'עדיין אין עובדים ב' + m[1] + '.'; }],
    [/^Move one here from another building’s tab\.$/, function(){ return 'העבירו לכאן עובד מלשונית של בניין אחר.'; }],
    [/^(\d+) of (\d+) steps done$/, function(m){ return m[1] + ' מתוך ' + m[2] + ' שלבים הושלמו'; }],
    [/^Whole building: (\d+) \/ (\d+) steps \((\d+)%\)$/, function(m){ return 'כל הבניין: ' + m[1] + ' / ' + m[2] + ' שלבים (' + m[3] + '%)'; }],
    [/^Floor (.+) · (\d+)\/(\d+) steps$/, function(m, t){ return 'קומה ' + t(m[1]) + ' · ' + m[2] + '/' + m[3] + ' שלבים'; }],
    [/^Floor (.+) \(new\)$/, function(m, t){ return 'קומה ' + t(m[1]) + ' (חדשה)'; }],
    [/^Floor (.+)$/, function(m, t){ return 'קומה ' + t(m[1]); }],
    [/^(\d+) floors found in this drawing$/, function(m){ return 'נמצאו ' + m[1] + ' קומות בשרטוט'; }],
    [/^(\d+) floors found — the first goes to the floor chosen above; change any of them here$/, function(m){ return 'נמצאו ' + m[1] + ' קומות — הראשונה תיכנס לקומה שנבחרה למעלה; אפשר לשנות כל אחת כאן'; }],
    [/^Save (\d+) floors$/, function(m){ return 'שמירת ' + m[1] + ' קומות'; }],
    [/^(\d+) floors imported: (.+)$/, function(m, t){ return 'יובאו ' + m[1] + ' קומות: ' + m[2].split(', ').map(t).join(', '); }],
    [/^Floor (.+) now uses the imported plan \((\d+) walls\)$/, function(m, t){ return 'קומה ' + t(m[1]) + ' משתמשת כעת בתוכנית שיובאה (' + m[2] + ' קירות)'; }],
    [/^Go back to the generic layout for floor (.+)\?$/, function(m, t){ return 'לחזור לפריסה הכללית של קומה ' + t(m[1]) + '?'; }],
    [/^Floor (.+) is back to the generic layout$/, function(m, t){ return 'קומה ' + t(m[1]) + ' חזרה לפריסה הכללית'; }],
    [/^Read (.+) — (.+)\.$/, function(m, t){ return 'נקרא ' + m[1] + ' — ' + t(m[2]) + '.'; }],
    [/^(.+) \(from file\)$/, function(m, t){ return t(m[1]) + ' (מהקובץ)'; }],
    [/^(.+) \(guessed from size\)$/, function(m, t){ return t(m[1]) + ' (נקבע לפי גודל השרטוט)'; }],
    [/^detected: (.+)$/, function(m, t){ return 'זוהה: ' + t(m[1]); }],
    [/^set to (.+)$/, function(m, t){ return 'הוגדר ל-' + t(m[1]); }],
    [/^PDF at 1:(.+)$/, function(m){ return 'PDF בקנה מידה 1:' + m[1]; }],
    [/^(\d+) lines$/, function(m){ return m[1] + ' קווים'; }],
    [/^(\d+) drawing lines$/, function(m){ return m[1] + ' קווי שרטוט'; }],
    [/^([\d.]+) m$/, function(m){ return m[1] + ' מ׳'; }],
    [/^([\d.]+) m × ([\d.]+) m$/, function(m){ return m[1] + ' מ׳ × ' + m[2] + ' מ׳'; }],
    [/^(\d+) walls?$/, function(m){ return m[1] + ' קירות'; }],
    [/^([\d.]+) m of wall$/, function(m){ return m[1] + ' מ׳ קיר'; }],
    [/^(.+) \(hidden in CAD\)$/, function(m){ return m[1] + ' (מוסתרת ב-CAD)'; }],
    [/^Plan is ([\d.]+) m × ([\d.]+) m — that looks unlikely for a building floor\. Check the units \/ drawing scale\.$/, function(m){ return 'התוכנית היא ' + m[1] + ' מ׳ × ' + m[2] + ' מ׳ — זה לא נראה סביר לקומה בבניין. בדקו את היחידות / קנה המידה.'; }],
    // wall names / workspace labels
    [/^the whole (.+)$/, function(m, t){ return t(m[1]) + ' כולו'; }],
    [/^(north|south|east|west)-side wall (W\d+)$/, function(m){ return 'קיר בצד ' + SIDE[m[1]] + ' ' + m[2]; }],
    [/^interior wall (W\d+)$/, function(m){ return 'קיר פנימי ' + m[1]; }],
    [/^wall (.+)$/, function(m){ return 'קיר ' + m[1]; }],
    [/^(left|middle|right) section, about ([\d.]+)m$/, function(m){ return 'קטע ' + SECTION[m[1]] + ', כ-' + m[2] + ' מ׳'; }],
    [/^([\d.]+)–([\d.]+) m from its (north|west) end$/, function(m){ return m[1] + '–' + m[2] + ' מ׳ מהקצה ה' + NAMES[m[3]]; }],
    [/^(.*?)\s*\((\d+) seg\)$/, function(m, t){ return t(m[1]) + (m[2] === '1' ? ' (קטע אחד)' : ' (' + m[2] + ' קטעים)'); }],
    // toasts / confirms
    [/^Worker added · (.+)$/, function(m){ return 'העובד נוסף · ' + m[1]; }],
    [/^(.+) is now: (.+)$/, function(m){ return m[1] + ' הוא כעת: ' + m[2]; }],
    [/^Trade cleared for (.+)$/, function(m){ return 'המקצוע של ' + m[1] + ' נוקה'; }],
    [/^Removed (.+)$/, function(m){ return m[1] + ' הוסר'; }],
    [/^Remove (.+)\? This also deletes their task history\.$/, function(m){ return 'להסיר את ' + m[1] + '? פעולה זו תמחק גם את היסטוריית המשימות.'; }],
    [/^(\d+) photo\(s\) flagged as not matching — worker notified$/, function(m){ return m[1] + ' תמונות סומנו כלא תואמות — העובד קיבל הודעה'; }],
    [/^Task status: (.+)$/, function(m, t){ return 'סטטוס משימה: ' + (STATUS[m[1]] || t(m[1])); }],
    [/^Task created and sent to (.+) on WhatsApp$/, function(m){ return 'המשימה נוצרה ונשלחה ל' + m[1] + ' בוואטסאפ'; }],
    [/^Task created, but WhatsApp delivery failed \((.*)\)$/, function(m){ return 'המשימה נוצרה, אך השליחה בוואטסאפ נכשלה (' + m[1] + ')'; }],
    [/^Task created for (.+)$/, function(m){ return 'המשימה נוצרה עבור ' + m[1]; }],
    [/^Started (.+)$/, function(m){ return 'התחילה ' + m[1]; }],
    [/^(.+) moved to (.+)$/, function(m){ return m[1] + ' הועבר/ה אל ' + m[2]; }],
    [/^Building "(.+)" created$/, function(m){ return 'הבניין "' + m[1] + '" נוצר'; }],
    [/^Delete building "(.+)"\? Its floor plans and steps are removed\.(?: Its (\d+) worker\(s\) become unassigned \(tasks stay\)\.)?$/, function(m){
      return 'למחוק את הבניין "' + m[1] + '"? תוכניות הקומות והשלבים שלו יימחקו.' + (m[2] ? ' ' + m[2] + ' עובדים שלו יהפכו ללא משויכים (המשימות נשארות).' : ''); }],
    [/^Couldn't convert this DWG \((.*)\)\. Export it as DXF from your CAD tool \(Save As -> DXF\) and upload that\.$/, function(m){ return 'לא ניתן להמיר את קובץ ה-DWG (' + m[1] + '). ייצאו אותו כ-DXF מתוכנת ה-CAD (שמירה בשם ← DXF) והעלו את הקובץ הזה.'; }]
  ];

  function tr(s){
    if(LANG !== 'he' || typeof s !== 'string') return s;
    var k = s.trim();
    if(!k) return s;
    var out = lookup(k, 0);
    if(out === null) return s;
    var i = s.indexOf(k);
    return s.slice(0, i) + out + s.slice(i + k.length);
  }
  function lookup(k, depth){
    if(Object.prototype.hasOwnProperty.call(HE, k)) return HE[k];
    if(WALLWORDS[k]) return WALLWORDS[k];
    if(STATUS[k]) return STATUS[k];
    if(depth > 4) return null;
    var nested = function(x){ var r = lookup(x.trim(), depth + 1); return r === null ? x : r; };
    for(var i = 0; i < HE_RULES.length; i++){
      var m = HE_RULES[i][0].exec(k);
      if(m) return HE_RULES[i][1](m, nested);
    }
    // "A · B" and "A — B": translate each part
    var seps = [' · ', ' — '];
    for(var j = 0; j < seps.length; j++){
      if(k.indexOf(seps[j]) > 0){
        var parts = k.split(seps[j]), hit = false;
        var mapped = parts.map(function(p){ var r = lookup(p.trim(), depth + 1); if(r !== null) hit = true; return r === null ? p : r; });
        if(hit) return mapped.join(seps[j]);
      }
    }
    if(k.indexOf('· ') === 0){ var r2 = lookup(k.slice(2).trim(), depth + 1); if(r2 !== null) return '· ' + r2; }
    return null;
  }
  window.tr = tr;

  if(LANG !== 'he') return;      // English: nothing below runs

  document.documentElement.lang = 'he';
  document.documentElement.classList.add('rtl');
  document.title = 'Babylon · לוח בקרה לאתר';

  var nodeRec = new WeakMap(), attrRec = new WeakMap();
  var ATTRS = ['title', 'placeholder'];
  function doText(n){
    var v = n.nodeValue, rec = nodeRec.get(n);
    if(rec && rec.out === v) return;
    var out = tr(v);
    nodeRec.set(n, {src: v, out: out});
    if(out !== v) n.nodeValue = out;
  }
  function doAttrs(el){
    ATTRS.forEach(function(a){
      if(!el.hasAttribute || !el.hasAttribute(a)) return;
      var v = el.getAttribute(a), rec = attrRec.get(el) || {};
      if(rec[a] === v) return;
      var out = tr(v);
      rec[a] = out; attrRec.set(el, rec);
      if(out !== v) el.setAttribute(a, out);
    });
  }
  function walk(root){
    if(root.nodeType === 3){ doText(root); return; }
    if(root.nodeType !== 1) return;
    var tag = root.tagName;
    if(tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA' || tag === 'INPUT' && root.type !== 'button') { doAttrs(root); return; }
    doAttrs(root);
    for(var c = root.firstChild; c; c = c.nextSibling) walk(c);
  }
  walk(document.body);
  new MutationObserver(function(muts){
    muts.forEach(function(m){
      if(m.type === 'childList'){ m.addedNodes.forEach(walk); }
      else if(m.type === 'characterData'){ doText(m.target); }
      else if(m.type === 'attributes'){ doAttrs(m.target); }
    });
  }).observe(document.body, {childList:true, subtree:true, characterData:true, attributes:true, attributeFilter:ATTRS});
})();
