import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Building2, LayoutDashboard, Search } from 'lucide-react';

export default function Header() {
  const location = useLocation();
  const isAdmin = location.pathname.includes('/admin');

  return (
    <header className="bg-white border-b border-[#E5E7EB] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="text-2xl font-bold text-[#111827] tracking-tight">
            MedPartners
          </Link>
          
          {!isAdmin && (
            <div className="hidden md:flex items-center gap-2 text-sm text-[#6B7280]">
              <Building2 size={16} />
              <select className="bg-transparent outline-none border-none cursor-pointer hover:text-[#111827] transition-colors">
                <option>Астана</option>
                <option>Алматы</option>
                <option>Шымкент</option>
              </select>
            </div>
          )}
        </div>

        <nav className="flex items-center gap-2 bg-[#F9FAFB] p-1 rounded-lg border border-[#E5E7EB]">
          <Link
            to="/"
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${
              !isAdmin 
                ? 'bg-white shadow-sm text-[#111827]' 
                : 'text-[#6B7280] hover:text-[#111827]'
            }`}
          >
            <Search size={16} />
            Поиск клиник
          </Link>
          <Link
            to="/admin"
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${
              isAdmin 
                ? 'bg-white shadow-sm text-[#111827]' 
                : 'text-[#6B7280] hover:text-[#111827]'
            }`}
          >
            <LayoutDashboard size={16} />
            Панель оператора
          </Link>
        </nav>
      </div>
    </header>
  );
}
