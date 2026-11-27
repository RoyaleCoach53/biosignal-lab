export const english = {
  nav: ["The journey", "Workbench", "Methods"],
  teaser: "An open atlas of biosignals",
  headline: ["Every thought", "begins with", "a signal."],
  intro: "Follow electrical activity from the brain and muscles to the signals we can record, interpret, and test.",
  enter: "Begin the journey", lab: "Open workbench", scroll: "Scroll to explore",
  chapters: [
    ["02 / ORIGIN", "A field made by many.", "Currents across neural membranes create extracellular fields. Aligned populations can contribute more strongly when their activity overlaps in time. What reaches the scalp is a mixture shaped by the tissues it travels through."],
    ["03 / ACQUISITION", "Capturing the invisible.", "EEG measures a voltage difference between electrodes on the scalp. An amplifier and analog filtering condition the signal before the analog-to-digital converter samples it. Scalp EEG does not resolve the firing of an individual neuron."],
    ["04 / PROCESSING", "From noise to insight.", "High-pass filtering attenuates slow components, low-pass attenuates faster ones, and a notch attenuates a narrow range around its center. Each can also alter meaningful signal components. A visible transient may remain after filtering."],
    ["05 / SPECTRUM", "Discover the rhythms within.", "Welch estimation divides a signal into overlapping segments, tapers each segment, estimates its power spectrum, and averages the estimates. Band power integrates this density over a frequency range. EEG bands describe frequencies, with boundaries that vary by convention."],
    ["06 / MUSCLE", "A different kind of signal.", "Surface EMG picks up contributions from muscle-fiber action potentials in active motor units. Its amplitude and spectrum depend on the muscle, electrode placement, and acquisition. RMS summarizes amplitude. Median frequency bisects integrated spectral power."],
  ],
  labIntro: "Run a controlled experiment. Change the sampling rate, signal condition, or filter, then compare the exact Python outputs.",
  methods: "A method you can inspect.",
  limits: "BioSignal Lab is open-source software for research and education. Its results depend on acquisition and processing choices. The PhysioNet pilot checks numerical agreement with MNE-Python under matched settings in a small sample. Filter padding can materially change outputs under different defaults.",
  release: "Release and downloads", source: "GitHub repository", quick: "Student quick start", contributing: "Contributing",
  notes: ["Scientific methods", "PhysioNet and MNE comparison", "Limits and interpretation"],
};

export const arabic = {
  nav: ["الرحلة", "مختبر الإشارات", "المنهجية"],
  teaser: "أطلس مفتوح للإشارات الحيوية",
  headline: ["كل فكرة", "تبدأ", "بإشارة."],
  intro: "تتبّع النشاط الكهربائي للدماغ والعضلات وصولاً إلى الإشارات التي نستطيع تسجيلها وتحليلها.",
  enter: "ابدأ الرحلة", lab: "افتح المختبر", scroll: "مرّر للاستكشاف",
  chapters: [
    ["٠٢ / المصدر", "مجال تصنعه خلايا كثيرة.", "تولّد التيارات العابرة لأغشية الخلايا العصبية مجالات كهربائية خارجها. قد يتعزز الإسهام عندما تتزامن خلايا ذات اتجاهات متقاربة."],
    ["٠٣ / الالتقاط", "التقاط ما لا يُرى.", "يقيس تخطيط كهربية الدماغ فرق الجهد بين أقطاب على فروة الرأس. تُضخَّم الإشارة وتُرشَّح تماثلياً قبل أخذ العينات. لا يفصل القياس نشاط خلية منفردة."],
    ["٠٤ / المعالجة", "من التشويش إلى التحليل.", "تخفف المرشحات الترددات البطيئة أو السريعة أو نطاقاً ضيقاً. وقد تغيّر أيضاً بعض مكونات الإشارة المهمة."],
    ["٠٥ / الطيف", "اكتشف الإيقاعات.", "تُقسَّم الإشارة في طريقة ويلش إلى مقاطع متداخلة، وتُطبَّق نافذة على كل مقطع، ثم يُحسب متوسط تقديرات الطيف."],
    ["٠٦ / العضلات", "إشارة من نوع آخر.", "يسجّل تخطيط كهربية العضلات السطحي إسهامات جهود الفعل الصادرة عن ألياف العضلات. تتأثر المقاييس بموضع الأقطاب وطريقة التسجيل."],
  ],
  labIntro: "غيّر معدل أخذ العينات أو المرشّح وقارن النتائج التي يحسبها محرك بايثون. عناصر التحكم بالإنجليزية.",
  methods: "منهجية يمكنك التحقق منها.",
  limits: "برنامج مفتوح المصدر للبحث والتعليم. تتأثر النتائج بإعدادات التسجيل والمعالجة. تقارن دراسة PhysioNet النتائج العددية مع MNE-Python في عينة صغيرة وعند استخدام إعدادات متطابقة.",
  release:"الإصدار والتنزيلات", source:"مستودع GitHub", quick:"دليل البدء", contributing:"المساهمة",
  notes:["المنهجية العلمية","مقارنة PhysioNet وMNE","القيود والتفسير"],
};
