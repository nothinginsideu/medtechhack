import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import ClientHome from './pages/ClientHome';
import AdminDashboard from './pages/AdminDashboard';

function App() {
  return (
    <div className="min-h-screen bg-[#F9FAFB] text-[#111827] font-sans">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<ClientHome />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
