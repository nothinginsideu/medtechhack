import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader2, TrendingUp } from 'lucide-react';

export default function ClientHome() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [isResident, setIsResident] = useState(true);
  const [activeTab, setActiveTab] = useState('Все');

  const tabs = ['Все', 'Лаборатория', 'Диагностика', 'Консультации', 'Процедуры'];

  const handleSearch = async (e) => {
    e.preventDefault();
    if (query.length < 2) return;
    
    setLoading(true);
    setSearched(true);
    
    try {
      const response = await axios.get(`http://localhost:8000/api/v1/search?q=${query}`);
      
      let data = response.data;
      
      // Если бэкенд пустой (нет реальных цен), показываем красивый мок для демо
      if (data.length === 0) {
        data = [
          {
            service_id: 1,
            name: "Общий анализ крови (ОАК)",
            specialty: "Лаборатория",
            prices: []
          }
        ];
      }
      
      // Инжектим красивые моковые цены для демо, если их нет в БД
      const dataWithMockPrices = data.map(item => ({
        ...item,
        prices: item.prices && item.prices.length > 0 ? item.prices : [
          { partner_id: 1, partner_name: "Инвитро (ул. Абая 12)", price: 2500 + Math.floor(Math.random() * 1000), price_nonresident: 4500, original_name: item.name, date: "24 Окт 2026" },
          { partner_id: 2, partner_name: "Олимп (пр. Достык 44)", price: 2800 + Math.floor(Math.random() * 1000), price_nonresident: 5000, original_name: item.name, date: "01 Ноя 2026" }
        ]
      }));

      setResults(dataWithMockPrices);

    } catch (error) {
      console.error(error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredResults = results.filter(item => {
    if (activeTab === 'Все') return true;
    return item.specialty === activeTab;
  });

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col items-center justify-center mb-12 mt-8">
        <h1 className="text-4xl font-bold text-[#111827] mb-3 tracking-tight">Поиск медицинских услуг</h1>
        <p className="text-[#6B7280] text-lg mb-8">Сравнивайте цены в клиниках и выбирайте лучшее предложение</p>
        
        <div className="w-full relative flex gap-4">
          <form className="flex-1 relative" onSubmit={handleSearch}>
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-[#6B7280]" />
            </div>
            <input
              type="text"
              className="block w-full pl-11 pr-4 py-4 border border-[#E5E7EB] rounded-lg bg-white text-base text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-medblue/20 focus:border-medblue transition-shadow shadow-sm"
              placeholder="Например: Общий анализ крови"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="absolute inset-y-0 right-2 flex items-center">
              <button 
                type="submit" 
                disabled={loading}
                className="bg-medblue hover:bg-medbluehover text-white px-6 py-2 rounded-md font-medium transition-colors"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Найти'}
              </button>
            </div>
          </form>

          {/* Toggle Resident */}
          <div className="flex items-center bg-white border border-[#E5E7EB] rounded-lg p-1 shadow-sm shrink-0">
            <button 
              onClick={() => setIsResident(true)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${isResident ? 'bg-[#F3F4F6] text-[#111827]' : 'text-[#6B7280] hover:text-[#111827]'}`}
            >
              Резидент
            </button>
            <button 
              onClick={() => setIsResident(false)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${!isResident ? 'bg-[#F3F4F6] text-[#111827]' : 'text-[#6B7280] hover:text-[#111827]'}`}
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
                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab 
                    ? 'bg-[#111827] text-white' 
                    : 'bg-white border border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB] hover:text-[#111827]'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="space-y-6">
            {!loading && filteredResults.length === 0 && (
              <div className="text-center py-16 bg-white border border-[#E5E7EB] rounded-xl">
                <p className="text-[#6B7280] text-lg">По запросу «{query}» ничего не найдено в категории «{activeTab}».</p>
              </div>
            )}

            {filteredResults.map((item) => (
              <div key={item.service_id} className="bg-white border border-[#E5E7EB] rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-5 border-b border-[#E5E7EB] flex justify-between items-center bg-[#F9FAFB]">
                  <h2 className="text-xl font-semibold text-[#111827]">{item.name}</h2>
                  <span className="bg-[#EFF6FF] text-[#1D4ED8] px-3 py-1 rounded-full text-sm font-medium">
                    {item.specialty || 'Общая'}
                  </span>
                </div>
                
                <div className="divide-y divide-[#F3F4F6]">
                  {item.prices.map((priceItem, pIndex) => {
                    const displayPrice = isResident ? priceItem.price : (priceItem.price_nonresident || priceItem.price * 1.5);
                    return (
                      <div key={pIndex} className="p-6 flex justify-between items-center hover:bg-[#F9FAFB] transition-colors">
                        <div className="flex flex-col gap-1">
                          <span className="font-medium text-[#111827] text-base">{priceItem.partner_name}</span>
                          <span className="text-sm text-[#6B7280]">По прайсу: {priceItem.original_name}</span>
                          <span className="text-xs text-[#9CA3AF]">Актуально: {priceItem.date || '01 Сен 2023'}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <button className="text-[#9CA3AF] hover:text-medblue transition-colors p-2" title="История цен">
                            <TrendingUp size={18} />
                          </button>
                          <div className="text-xl font-bold text-[#059669]">
                            {displayPrice ? `${displayPrice} ₸` : 'По запросу'}
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
    </div>
  );
}
