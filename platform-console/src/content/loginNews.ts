export type LoginNewsCard = {
  id: string;
  title: string;
  body: string;
  href?: string;
  hrefLabel?: string;
};

export const LOGIN_NEWS_CARDS: LoginNewsCard[] = [
  {
    id: "whats-new",
    title: "Что нового в Flexity",
    body: "Публичный сайт с направлениями внедрения и рабочее место менеджера в консоли развиваются поэтапно — без обещания «всё сразу».",
    href: "https://www.flexity.asia/solutions/",
    hrefLabel: "Посмотреть решения",
  },
  {
    id: "manager-workspace",
    title: "Рабочее место менеджера",
    body: "CRM, клиенты и заявки в консоли платформы — на staging, объём функций расширяется итерациями.",
  },
  {
    id: "insights",
    title: "Инсайты для бизнеса",
    body: "Рубрики про CRM, учёт и автоматизацию — статический индекс на сайте, публикации позже.",
    href: "https://www.flexity.asia/insights/",
    hrefLabel: "Открыть инсайты",
  },
  {
    id: "demo",
    title: "Демо и разбор процесса",
    body: "Заявка через контакты на сайте. Покажем, как Flexity может лечь на текущий процесс продаж и обслуживания.",
    href: "https://www.flexity.asia/demo/",
    hrefLabel: "Запросить демо",
  },
];

export const LOGIN_RESOURCE_LINKS = [
  { label: "Инсайты", href: "https://www.flexity.asia/insights/" },
  { label: "Кейсы", href: "https://www.flexity.asia/cases/" },
  { label: "Демо", href: "https://www.flexity.asia/demo/" },
  { label: "Решения", href: "https://www.flexity.asia/solutions/" },
] as const;
