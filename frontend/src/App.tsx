import { useEffect, useState, type MouseEvent } from 'react';
import {
  Activity, Bell, BookOpen, BrainCircuit, Camera, ChartNoAxesColumnIncreasing,
  ChevronDown, Cpu, Ellipsis, Gauge, Home, Leaf, Lightbulb, PanelLeftClose,
  Settings, Sprout, Waves,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import TomatoHealthPage from './pages/TomatoHealth';
import {
  CameraPage, ExperiencePage, HardwarePage, HistoryPage, LearningPage,
  LiveSensorsPage, DecisionPage, SettingsPage,
} from './pages/Pages';

const navGroups = [
  { title: 'OVERVIEW', items: [{ label: 'Dashboard', href: '/', icon: Home }] },
  { title: 'MONITOR', items: [{ label: 'Live Sensors', href: '/sensors', icon: Activity }, { label: 'Camera', href: '/camera', icon: Camera }, { label: 'Tomato Health', href: '/tomato-health', icon: Leaf }] },
  { title: 'INTELLIGENCE', items: [{ label: 'Decision Center', href: '/decisions', icon: BrainCircuit }, { label: 'Experience Memory', href: '/experience', icon: BookOpen }, { label: 'Learning', href: '/learning', icon: Lightbulb }] },
  { title: 'ANALYTICS', items: [{ label: 'History & Trends', href: '/history', icon: ChartNoAxesColumnIncreasing }] },
  { title: 'SYSTEM', items: [{ label: 'Hardware', href: '/hardware', icon: Cpu }, { label: 'Settings', href: '/settings', icon: Settings }] },
];

const allNavItems = navGroups.flatMap((group) => group.items);

function Brand() {
  return <a className="brand" href="/" aria-label="AgriSight dashboard">
    <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 42 42" fill="none"><rect width="42" height="42" rx="14" fill="currentColor"/><path d="M10 30c8-.5 15.6-7 18.2-17.2.4-1.4.5-2.9.5-4.2-3 .2-5.8.9-8.3 2.2C13.4 14.4 9.7 22 10 30Z" fill="#DDF3E5"/><path d="M11 32c5.5-7 10.1-11.1 17-16m-14 10c-.2-3.1.4-5.9 1.8-8.5m4.6 4.7c3.4 0 6.1-1.4 8.1-3.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><path d="M8 34h26" stroke="#A9D9BD" strokeWidth="2" strokeLinecap="round"/></svg></span>
    <span className="brand-word">Agri<span>Sight</span></span>
  </a>;
}

function Sidebar({ pathname }: { pathname: string }) {
  return <aside className="sidebar">
    <div className="sidebar-brand"><Brand /><button className="sidebar-collapse" aria-label="Sidebar navigation"><PanelLeftClose size={17} /></button></div>
    <div className="farm-switcher"><span className="farm-avatar"><Sprout size={17} /></span><span className="farm-switcher-copy"><strong>Field overview</strong><small>Sample farm</small></span><ChevronDown size={15} /></div>
    <nav className="sidebar-nav" aria-label="Main navigation">
      {navGroups.map((group) => <div className="nav-group" key={group.title}>
        <div className="nav-group-title">{group.title}</div>
        {group.items.map(({ label, href, icon: Icon }) => <a key={href} href={href} title={label} className={`nav-link ${pathname === href ? 'nav-active' : ''}`} aria-current={pathname === href ? 'page' : undefined}><Icon size={18} strokeWidth={1.8} /><span>{label}</span>{pathname === href && <i className="nav-active-mark" />}</a>)}
      </div>)}
    </nav>
    <div className="sidebar-bottom"><div className="sidebar-help"><span className="help-icon"><Waves size={17} /></span><div><strong>Growing with you</strong><small>Clear guidance, season by season.</small></div></div><div className="sidebar-profile"><span className="profile-avatar">F</span><span><strong>Farmer</strong><small>Farm account</small></span><Ellipsis size={18} /></div></div>
  </aside>;
}

function MobileNavigation({ pathname, onNavigate }: { pathname: string; onNavigate: (event: MouseEvent<HTMLDivElement>) => void }) {
  const [open, setOpen] = useState(false);
  const primary = allNavItems.filter((item) => ['/', '/sensors', '/camera', '/decisions'].includes(item.href));
  const more = allNavItems.filter((item) => !['/', '/sensors', '/camera', '/decisions'].includes(item.href));
  return <>
    {open && <div className="mobile-more-menu" onClick={(event) => { onNavigate(event); setOpen(false); }} aria-label="More pages">{more.map(({ label, href, icon: Icon }) => <a key={href} href={href} className={pathname === href ? 'is-current' : ''}><Icon size={17} /><span>{label}</span></a>)}</div>}
    <nav className="mobile-nav" aria-label="Mobile navigation" onClick={onNavigate}>
      {primary.map(({ label, href, icon: Icon }) => <a key={href} href={href} className={pathname === href ? 'mobile-nav-active' : ''} aria-current={pathname === href ? 'page' : undefined}><Icon size={19} /><span>{label === 'Decision Center' ? 'Decisions' : label}</span></a>)}
      <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}><Ellipsis size={20} /><span>More</span></button>
    </nav>
  </>;
}

function CurrentPage({ pathname }: { pathname: string }) {
  switch (pathname) {
    case '/': return <Dashboard />;
    case '/sensors': return <LiveSensorsPage />;
    case '/camera': return <CameraPage />;
    case '/tomato-health': return <TomatoHealthPage />;
    case '/decisions': return <DecisionPage />;
    case '/experience': return <ExperiencePage />;
    case '/learning': return <LearningPage />;
    case '/history': return <HistoryPage />;
    case '/hardware': return <HardwarePage />;
    case '/settings': return <SettingsPage />;
    default: return <Dashboard />;
  }
}

export default function App() {
  const [pathname, setPathname] = useState(window.location.pathname.replace(/\/$/, '') || '/');

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname.replace(/\/$/, '') || '/');
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    const current = allNavItems.find((item) => item.href === pathname);
    document.title = `${current?.label ?? 'Dashboard'} · AgriSight`;
  }, [pathname]);

  function handleNavigation(event: MouseEvent<HTMLElement>) {
    const target = event.target as HTMLElement;
    const anchor = target.closest('a');
    if (!anchor || anchor.target === '_blank' || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const href = anchor.getAttribute('href');
    if (!href?.startsWith('/') || href.startsWith('//')) return;
    event.preventDefault();
    if (window.location.pathname !== href) window.history.pushState({}, '', href);
    setPathname(href.replace(/\/$/, '') || '/');
    const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
    window.scrollTo({ top: 0, behavior });
  }

  return <div className="app-frame" onClick={handleNavigation}>
    <div className="desktop-sidebar"><Sidebar pathname={pathname} /></div>
    <div className="content-shell">
      <header className="topbar">
        <div className="mobile-brand-wrap"><Brand /></div>
        <div className="topbar-context"><strong>Farm Overview</strong><span>Sample field</span></div>
        <div className="topbar-spacer" />
        <span className="demo-indicator"><i /> System online · demo</span>
        <div className="topbar-updated"><span>Last updated</span><strong>Just now</strong></div>
        <button type="button" className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
        <button type="button" className="user-button" aria-label="Farmer profile"><span className="user-avatar">F</span><span className="user-button-copy"><strong>Farmer</strong><small>Field account</small></span><ChevronDown size={14} /></button>
      </header>
      <main className="main-content" key={pathname}><CurrentPage pathname={pathname} /></main>
      <MobileNavigation pathname={pathname} onNavigate={handleNavigation as (event: MouseEvent<HTMLDivElement>) => void} />
    </div>
  </div>;
}
