import React, { useState } from 'react';
import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Package, Users, Video, Wand2, Settings, LogOut, Image, ShoppingBag, Target, ChevronLeft, ChevronRight, FileImage, Search, ChevronDown, UserCog, Blocks, BarChart3 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function Layout() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout, hasRole } = useAuth();
    const { showSuccess } = useToast();
    const [expandedMenus, setExpandedMenus] = useState({ Audience: false, Research: false, 'Script Factory': false, Analytics: false });
    const [isCollapsed, setIsCollapsed] = useState(false);

    const handleLogout = async () => {
        await logout();
        showSuccess('Logged out successfully');
        navigate('/login');
    };

    const menuItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        {
            icon: Search,
            label: 'Research',
            subItems: [
                { label: 'Research', path: '/research' },
                { label: 'Scrape Brand Ads', path: '/research/brand-scrapes' },
                { label: 'Settings', path: '/research/settings' }
            ]
        },
        {
            icon: Blocks,
            label: 'Script Factory',
            subItems: [
                { label: 'Build Creatives', path: '/build-creatives' },
                { label: 'Modular Matrix', path: '/modular-ads' },
                { label: 'Ad Modules Library', path: '/ad-modules-library' },
            ]
        },
        {
            icon: Users,
            label: 'Audience',
            subItems: [
                { label: 'Customer Profiles', path: '/profiles' },
                { label: 'AI Personas', path: '/personas' }
            ]
        },
        { icon: Image, label: 'Winning Ads', path: '/winning-ads' },
        { icon: FileImage, label: 'Generated Ads', path: '/generated-ads' },
        { icon: Target, label: 'Facebook Campaigns', path: '/facebook-campaigns' },
        {
            icon: BarChart3,
            label: 'Analytics',
            subItems: [
                { label: 'Reporting', path: '/reporting' },
                { label: 'Ad Remix', path: '/ad-remix' },
            ]
        },
    ];

    const toggleMenu = (label) => {
        setExpandedMenus(prev => ({
            ...prev,
            [label]: !prev[label]
        }));
    };

    return (
        <div className="flex h-screen bg-background text-foreground overflow-hidden">
            {/* Sidebar */}
            <aside className={`${isCollapsed ? 'w-20' : 'w-64'} bg-card/80 backdrop-blur-xl border-r border-white/5 flex flex-col shadow-[4px_0_24px_rgba(0,0,0,0.5)] transition-all duration-300 ease-in-out relative z-20`}>
                {/* Toggle Button */}
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="absolute -right-3 top-9 bg-card border border-white/10 rounded-full p-1.5 shadow-lg hover:bg-white/5 hover:border-primary/50 text-muted-foreground hover:text-primary transition-all z-10"
                >
                    {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                </button>

                <div className={`p-6 border-b border-white/5 ${isCollapsed ? 'px-4' : ''}`}>
                    <div className={`flex items-center gap-3 ${isCollapsed ? 'justify-center' : ''}`}>
                        <div className="w-10 h-10 bg-black/40 rounded-xl flex items-center justify-center overflow-hidden border border-white/10 flex-shrink-0 shadow-inner">
                            <img src="/tsi_logo.svg" alt="Townsquare Interactive" className="w-full h-full object-cover opacity-90" />
                        </div>
                        {!isCollapsed && (
                            <div className="overflow-hidden whitespace-nowrap">
                                <h1 className="text-xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70" title="Townsquare Interactive">TSI</h1>
                                <p className="text-xs text-primary/80 font-medium tracking-wide uppercase mt-0.5">Ad Creative Studio</p>
                            </div>
                        )}
                    </div>
                </div>

                <nav className="flex-1 p-4 space-y-1 overflow-y-auto overflow-x-hidden">
                    {menuItems.map((item) => {
                        const Icon = item.icon;

                        if (item.subItems) {
                            const isExpanded = expandedMenus[item.label];
                            const isActive = item.subItems.some(sub => location.pathname === sub.path);

                            return (
                                <div key={item.label} className="space-y-1">
                                    <button
                                        onClick={() => {
                                            if (!isCollapsed) toggleMenu(item.label);
                                            if (item.subItems?.[0]?.path) navigate(item.subItems[0].path);
                                        }}
                                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group ${isActive
                                            ? 'bg-primary/10 text-primary font-medium border border-primary/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]'
                                            : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                                            } ${isCollapsed ? 'justify-center px-2' : ''}`}
                                        title={isCollapsed ? item.label : ''}
                                    >
                                        <Icon size={20} className={`transition-all duration-300 flex-shrink-0 ${isActive ? 'text-primary drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]' : 'text-muted-foreground group-hover:text-primary/70'}`} />
                                        {!isCollapsed && (
                                            <>
                                                <span className="flex-1 text-left whitespace-nowrap overflow-hidden">{item.label}</span>
                                                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                            </>
                                        )}
                                    </button>

                                    {!isCollapsed && isExpanded && (
                                        <div className="pl-11 space-y-1 mt-1">
                                            {item.subItems.map(subItem => {
                                                const isSubActive = location.pathname === subItem.path;
                                                return (
                                                    <Link
                                                        key={subItem.path}
                                                        to={subItem.path}
                                                        className={`block px-3 py-2 rounded-lg text-sm transition-all duration-200 ${isSubActive
                                                            ? 'text-primary bg-primary/10 font-medium border border-primary/10'
                                                            : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                                                            }`}
                                                    >
                                                        {subItem.label}
                                                    </Link>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        }

                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group ${isActive
                                    ? 'bg-primary/10 text-primary font-medium border border-primary/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]'
                                    : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                                    } ${isCollapsed ? 'justify-center px-2' : ''}`}
                                title={isCollapsed ? item.label : ''}
                            >
                                <Icon size={20} className={`transition-all duration-300 flex-shrink-0 ${isActive ? 'text-primary drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]' : 'text-muted-foreground group-hover:text-primary/70'}`} />
                                {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">{item.label}</span>}
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-white/5 bg-black/20">
                    {hasRole('admin') && (
                        <Link
                            to="/users"
                            className={`flex items-center gap-3 px-4 py-3 w-full rounded-xl transition-all duration-300 group ${
                                location.pathname === '/users'
                                    ? 'bg-primary/10 text-primary font-medium border border-primary/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]'
                                    : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                            } ${isCollapsed ? 'justify-center px-2' : ''}`}
                            title={isCollapsed ? 'User Management' : ''}
                        >
                            <UserCog size={20} className={`transition-all duration-300 flex-shrink-0 ${
                                location.pathname === '/users'
                                    ? 'text-primary drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]'
                                    : 'text-muted-foreground group-hover:text-primary/70'
                            }`} />
                            {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">User Management</span>}
                        </Link>
                    )}
                    <Link
                        to="/settings"
                        className={`flex items-center gap-3 px-4 py-3 w-full rounded-xl transition-all duration-300 group mt-1 ${
                            location.pathname === '/settings'
                                ? 'bg-primary/10 text-primary font-medium border border-primary/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]'
                                : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                        } ${isCollapsed ? 'justify-center px-2' : ''}`}
                        title={isCollapsed ? 'Settings' : ''}
                    >
                        <Settings size={20} className={`transition-all duration-300 flex-shrink-0 ${
                            location.pathname === '/settings'
                                ? 'text-primary drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]'
                                : 'text-muted-foreground group-hover:text-primary/70'
                        }`} />
                        {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">Settings</span>}
                    </Link>

                    {!isCollapsed && user && (
                        <div className="px-4 py-3 mt-3 bg-white/5 border border-white/5 rounded-xl backdrop-blur-sm">
                            <div className="text-sm font-medium text-foreground truncate">
                                {user.name || user.email}
                            </div>
                            <div className="text-xs text-muted-foreground truncate">{user.email}</div>
                        </div>
                    )}

                    <button
                        onClick={handleLogout}
                        className={`flex items-center gap-3 px-4 py-3 w-full text-destructive hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 mt-2 ${isCollapsed ? 'justify-center px-2' : ''}`}
                        title={isCollapsed ? 'Logout' : ''}
                    >
                        <LogOut size={20} className="flex-shrink-0" />
                        {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">Logout</span>}
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto relative bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-background via-background to-black">
                {/* Subtle Background Glow Map */}
                <div className="absolute top-0 inset-x-0 h-[400px] bg-primary/5 blur-[120px] pointer-events-none rounded-full translate-y-[-50%] z-0"></div>
                
                <div className="p-8 max-w-[1600px] mx-auto relative z-10 w-full">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}
