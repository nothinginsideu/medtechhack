import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader2, TrendingUp, X, MapPin, Building2, Phone } from 'lucide-react';

export default function ClientHome() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [isResident, setIsResident] = useState(true);
  const [activeTab, setActiveTab] = useState('Все');
  
  const [selectedPartner, setSelectedPartner] = useState(null);
  const [partnerModalLoading, setPartnerModalLoading] = useState(false);

  const tabs = ['Все', 'Лаборатория', 'Диагностика', 'Консультации', 'Процедуры'];

  const handleSearch = async (e) => {
    e.preventDefault();
    if (query.length < 2) return;
    
    setLoading(true);
    setSearched(true);
    
    try {
      const response = await axios.get(`http://localhost:8000/api/v1/search?q=${query}`);
      setResults(response.data);
    } catch (error) {
      console.error(error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const openPartnerModal = async (partnerId) => {
    setPartnerModalLoading(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/v1/partner/${partnerId}`);
      setSelectedPartner(response.data);
    } catch (error) {
      console.error("Ошибка загрузки профиля клиники:", error);
    } finally {
      setPartnerModalLoading(false);
    }
  };

  const filteredResults = results.filter(item => {
    if (activeTab === 'Все') return true;
    return item.specialty === activeTab;
  });

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col items-center justify-center mb-10 mt-6">
        <h1 className="text-3xl font-bold text-[#111827] mb-2 tracking-tight">Поиск медицинских услуг</h1>
        <p className="text-[#6B7280] text-base mb-6">Сравнивайте цены в клиниках и выбирайте лучшее предложение</p>
        
        <div className="w-full relative flex gap-3">
          <form className="flex-1 relative" onSubmit={handleSearch}>
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-[#9CA3AF]" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-4 py-3 border border-[#D1D5DB] rounded-md bg-white text-sm text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] transition-shadow shadow-sm"
              placeholder="Введите название услуги..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="absolute inset-y-0 right-1.5 flex items-center">
              <button 
                type="submit" 
                disabled={loading}
                className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-5 py-1.5 rounded text-sm font-medium transition-colors"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Найти'}
              </button>
            </div>
          </form>

          {/* Toggle Resident */}
          <div className="flex items-center bg-[#F3F4F6] border border-[#E5E7EB] rounded-md p-1 shrink-0">
            <button 
              onClick={() => setIsResident(true)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${isResident ? 'bg-white text-[#111827] shadow-sm' : 'text-[#6B7280] hover:text-[#111827]'}`}
            >
              Резидент
            </button>
            <button 
              onClick={() => setIsResident(false)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${!isResident ? 'bg-white text-[#111827] shadow-sm' : 'text-[#6B7280] hover:text-[#111827]'}`}
            >
              Нерезидент
            </button>
          </div>
        </div>
      </div>

      {searched && (
        <>
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {tabs.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab 
                    ? 'bg-[#111827] text-white' 
                    : 'bg-white border border-[#D1D5DB] text-[#4B5563] hover:border-[#9CA3AF]'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {!loading && filteredResults.length === 0 && (
              <div className="text-center py-12 bg-white border border-[#E5E7EB] rounded-md">
                <Search className="mx-auto h-8 w-8 text-[#D1D5DB] mb-3" />
                <p className="text-[#374151] font-medium">Ничего не найдено</p>
                <p className="text-[#6B7280] text-sm mt-1">Попробуйте изменить запрос</p>
              </div>
            )}

            {filteredResults.map((item) => (
              <div key={item.service_id} className="bg-white border border-[#E5E7EB] rounded-md shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-[#E5E7EB] flex justify-between items-center bg-[#F9FAFB]">
                  <h2 className="text-base font-semibold text-[#111827]">{item.name}</h2>
                  <span className="bg-[#EFF6FF] text-[#1D4ED8] px-2.5 py-0.5 rounded text-xs font-medium">
                    {item.specialty || 'Общая'}
                  </span>
                </div>
                
                <div className="divide-y divide-[#F3F4F6]">
                  {item.prices.map((priceItem, pIndex) => {
                    const displayPrice = isResident ? priceItem.price_resident : priceItem.price_nonresident;
                    const hasForeignCurrency = priceItem.currency_original && priceItem.currency_original !== 'KZT';
                    
                    return (
                      <div key={pIndex} className="p-5 flex justify-between items-center hover:bg-[#F9FAFB] transition-colors">
                        <div className="flex flex-col gap-1 w-2/3">
                          <button 
                            onClick={() => openPartnerModal(priceItem.partner_id)}
                            className="text-left font-medium text-[#2563EB] text-sm hover:underline hover:text-[#1D4ED8] flex items-center gap-1 w-fit"
                          >
                            <Building2 size={14} className="text-[#9CA3AF]"/>
                            {priceItem.partner_name}
                          </button>
                          <span className="text-xs text-[#6B7280]">По прайсу: {priceItem.original_name}</span>
                          <span className="text-[11px] font-medium text-[#059669] bg-[#ECFDF5] w-fit px-2 py-0.5 rounded-sm mt-1">
                            Актуально: {priceItem.date}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex flex-col items-end">
                            <div className="text-lg font-bold text-[#111827]">
                              {displayPrice ? `${Number(displayPrice).toLocaleString('ru-RU')} ₸` : 'По запросу'}
                            </div>
                            {hasForeignCurrency && (
                              <div className="text-xs text-[#9CA3AF]">
                                Оригинал: {Number(priceItem.price_original).toLocaleString('ru-RU')} {priceItem.currency_original}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Partner Modal */}
      {selectedPartner && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-md shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-[#E5E7EB]">
              <h2 className="text-lg font-bold text-[#111827]">{selectedPartner.name}</h2>
              <button onClick={() => setSelectedPartner(null)} className="text-[#9CA3AF] hover:text-[#111827]">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-5 overflow-y-auto">
              <div className="grid grid-cols-2 gap-4 mb-6 bg-[#F9FAFB] p-4 rounded-md border border-[#E5E7EB]">
                <div className="flex items-start gap-2">
                  <MapPin size={16} className="text-[#6B7280] mt-0.5"/>
                  <div>
                    <div className="text-xs text-[#6B7280] uppercase tracking-wider mb-0.5">Адрес</div>
                    <div className="text-sm font-medium text-[#111827]">{selectedPartner.city}, {selectedPartner.address}</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Building2 size={16} className="text-[#6B7280] mt-0.5"/>
                  <div>
                    <div className="text-xs text-[#6B7280] uppercase tracking-wider mb-0.5">БИН</div>
                    <div className="text-sm font-medium text-[#111827]">{selectedPartner.bin || 'Не указан'}</div>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Phone size={16} className="text-[#6B7280] mt-0.5"/>
                  <div>
                    <div className="text-xs text-[#6B7280] uppercase tracking-wider mb-0.5">Контакты</div>
                    <div className="text-sm font-medium text-[#111827]">{selectedPartner.phone || 'Не указан'}</div>
                  </div>
                </div>
              </div>

              <h3 className="text-sm font-semibold text-[#111827] mb-3">Полный прайс-лист клиники</h3>
              <div className="border border-[#E5E7EB] rounded-md overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                    <tr>
                      <th className="px-4 py-2 font-medium text-[#374151]">Услуга</th>
                      <th className="px-4 py-2 font-medium text-[#374151]">Спецификация</th>
                      <th className="px-4 py-2 font-medium text-[#374151]">Цена (Рез)</th>
                      <th className="px-4 py-2 font-medium text-[#374151]">Цена (Нерез)</th>
                      <th className="px-4 py-2 font-medium text-[#374151]">Оригинал</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E7EB]">
                    {selectedPartner.price_list.map((p, i) => (
                      <tr key={i} className="hover:bg-[#F9FAFB]">
                        <td className="px-4 py-2 font-medium text-[#111827]">{p.service_name}</td>
                        <td className="px-4 py-2 text-[#6B7280]">{p.specialty}</td>
                        <td className="px-4 py-2 text-[#111827]">{p.price_resident} ₸</td>
                        <td className="px-4 py-2 text-[#6B7280]">{p.price_nonresident} ₸</td>
                        <td className="px-4 py-2 text-[#9CA3AF] text-xs">
                          {p.currency_original !== 'KZT' ? `${p.price_original} ${p.currency_original}` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
