import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader2, TrendingUp, X, MapPin, Building2, Phone } from 'lucide-react';
import { useServiceFilters } from '../hooks/useServiceFilters';

export default function ClientHome({ selectedCity }) {
  const {
    query,
    setQuery,
    activeCategory,
    setActiveCategory,
    isResident,
    setIsResident,
    loading,
    searched,
    filteredResults
  } = useServiceFilters([], selectedCity);
  
  const [selectedPartner, setSelectedPartner] = useState(null);
  const [partnerModalLoading, setPartnerModalLoading] = useState(false);

  // States for Price History / Dynamics
  const [expandedHistory, setExpandedHistory] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // States for AI Chat Assistant
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: 'Здравствуйте! Я ваш медицинский ИИ-ассистент MedPartners. Опишите свои симптомы или жалобы (например, "болит поясница и отдает в ногу"), и я помогу найти нужные услуги, исследования и сравнить цены в клиниках.',
      services: []
    }
  ]);

  const toggleHistory = async (serviceId, partnerId, rawName) => {
    const key = `${serviceId}_${partnerId}`;
    if (expandedHistory === key) {
      setExpandedHistory(null);
      return;
    }
    
    setExpandedHistory(key);
    setHistoryLoading(true);
    try {
      const isVirtual = typeof serviceId === 'string' && serviceId.startsWith('unlinked_');
      const params = new URLSearchParams();
      if (isVirtual) {
        params.append('raw_name', rawName);
      } else {
        params.append('service_id', serviceId);
      }
      const response = await axios.get(`http://localhost:8000/api/v1/partners/${partnerId}/history?${params.toString()}`);
      setHistoryData(response.data);
    } catch (error) {
      console.error("Ошибка загрузки истории цен:", error);
      setHistoryData([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: chatInput,
      services: []
    };
    
    setMessages(prev => [...prev, userMsg]);
    const currentInput = chatInput;
    setChatInput("");
    setChatLoading(true);
    
    try {
      const response = await axios.post('http://localhost:8000/api/v1/search/assistant', {
        message: currentInput
      });
      
      const botMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: `${response.data.analysis}\n\n**Рекомендации:**\n${response.data.recommendations.map(r => `• ${r}`).join('\n')}`,
        services: response.data.services || []
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (error) {
      console.error("Ошибка ассистента:", error);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: 'Извините, возникли проблемы при связи с ИИ. Попробуйте еще раз.',
        services: []
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const formatBotText = (text) => {
    return text.split('\n').map((line, i) => {
      let formatted = line;
      const boldRegex = /\*\*(.*?)\*\*/g;
      formatted = formatted.replace(boldRegex, '<strong>$1</strong>');
      return (
        <div key={i} className="mb-1" dangerouslySetInnerHTML={{ __html: formatted }} />
      );
    });
  };

  const renderHistoryChart = (data) => {
    if (historyLoading) {
      return (
        <div className="flex items-center gap-2 text-xs text-[#6B7280] p-3 bg-[#F9FAFB] rounded border border-[#E5E7EB] mt-2 animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Загрузка истории изменений...
        </div>
      );
    }
    if (!data || data.length === 0) {
      return (
        <div className="text-xs text-[#6B7280] p-3 bg-[#F9FAFB] rounded border border-[#E5E7EB] mt-2">
          Нет исторических данных об изменениях цены для этой услуги в клинике.
        </div>
      );
    }
    if (data.length === 1) {
      const p = isResident ? data[0].price : data[0].price_nonresident;
      return (
        <div className="flex gap-4 items-center text-xs text-[#4B5563] p-3 bg-[#F9FAFB] rounded border border-[#E5E7EB] mt-2">
          <span>Период действия цены ({data[0].date}):</span>
          <span className="font-semibold text-[#111827]">{p.toLocaleString('ru-RU')} ₸</span>
          <span className="text-[#9CA3AF]">(Только одна точка цены в базе)</span>
        </div>
      );
    }
    
    const width = 300;
    const height = 80;
    const padding = 15;
    
    const prices = data.map(d => isResident ? d.price : d.price_nonresident);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;
    
    const points = data.map((d, index) => {
      const x = padding + (index / (data.length - 1)) * (width - 2 * padding);
      const currentPrice = isResident ? d.price : d.price_nonresident;
      const y = height - padding - ((currentPrice - minPrice) / priceRange) * (height - 2 * padding);
      return { x, y, label: `${currentPrice.toLocaleString('ru-RU')} ₸`, date: d.date.substring(5) };
    });
    
    const polylinePoints = points.map(p => `${p.x},${p.y}`).join(' ');
    
    return (
      <div className="flex flex-col gap-2 mt-2 bg-[#F9FAFB] p-3 rounded border border-[#E5E7EB] w-full animate-in fade-in duration-200">
        <div className="flex justify-between items-center">
          <span className="text-[11px] font-semibold text-[#374151]">Динамика цены (за прошлые периоды):</span>
          <span className="text-[11px] text-[#2563EB] font-semibold">
            Тренд: {points[0].label} → {points[points.length - 1].label}
          </span>
        </div>
        
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative">
            <svg width={width} height={height} className="overflow-visible">
              <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#F3F4F6" strokeDasharray="3" />
              <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#E5E7EB" />
              
              <polyline
                fill="none"
                stroke="#2563EB"
                strokeWidth="2"
                points={polylinePoints}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              
              {points.map((p, i) => (
                <g key={i}>
                  <circle cx={p.x} cy={p.y} r="3.5" fill="#2563EB" stroke="#FFFFFF" strokeWidth="1.5" />
                  {(i === 0 || i === points.length - 1) && (
                    <text x={p.x} y={p.y - 6} textAnchor="middle" className="text-[9px] font-bold fill-[#374151]">
                      {p.label}
                    </text>
                  )}
                  <text x={p.x} y={height - 2} textAnchor="middle" className="text-[8px] fill-[#9CA3AF]">
                    {p.date}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          
          <div className="flex-1 flex flex-col gap-1 max-h-[70px] overflow-y-auto pr-1">
            {data.map((d, idx) => {
              const p = isResident ? d.price : d.price_nonresident;
              return (
                <div key={idx} className="flex justify-between items-center text-[10px] text-[#4B5563]">
                  <span>{d.date}</span>
                  <span className="font-semibold text-[#111827]">{p.toLocaleString('ru-RU')} ₸</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const tabs = ['Все', 'Лаборатория', 'Диагностика', 'Консультации', 'Процедуры'];

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

  const handleSearchSubmit = (e) => {
    e.preventDefault();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col items-center justify-center mb-10 mt-6">
        <h1 className="text-3xl font-bold text-[#111827] mb-2 tracking-tight">Поиск медицинских услуг</h1>
        <p className="text-[#6B7280] text-base mb-6">Сравнивайте цены в клиниках и выбирайте лучшее предложение</p>
        
        <div className="w-full relative flex gap-3">
          <form className="flex-1 relative" onSubmit={handleSearchSubmit}>
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

      {!searched && (
        <div className="flex flex-col items-center mt-12 bg-white border border-[#E5E7EB] rounded-lg p-8 shadow-sm">
          <TrendingUp className="h-8 w-8 text-[#2563EB] mb-3 animate-pulse" />
          <h2 className="text-base font-semibold text-[#111827] mb-1">Быстрый поиск</h2>
          <p className="text-sm text-[#6B7280] mb-6 text-center">Выберите одну из популярных услуг, чтобы сравнить цены</p>
          
          <div className="flex flex-wrap gap-2 justify-center max-w-lg">
            {[
              { label: '🩸 Общий анализ крови (ОАК)', query: 'анализ крови' },
              { label: '🧠 МРТ головного мозга', query: 'МРТ' },
              { label: '🩺 Приём терапевта', query: 'терапевт' },
              { label: '🤰 УЗИ', query: 'УЗИ' },
              { label: '🦠 ПЦР тест', query: 'ПЦР' },
              { label: '🦷 Консультация стоматолога', query: 'стоматолог' }
            ].map((item) => (
              <button
                key={item.label}
                onClick={() => setQuery(item.query)}
                className="px-4 py-2 bg-[#F3F4F6] hover:bg-[#E5E7EB] text-sm font-medium text-[#374151] rounded-md transition-all flex items-center gap-1.5 cursor-pointer shadow-sm border border-[#E5E7EB] hover:scale-105 active:scale-95 duration-100"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {searched && (
        <>
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {tabs.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveCategory(tab)}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  activeCategory === tab 
                    ? 'bg-[#111827] text-white' 
                    : 'bg-white border border-[#D1D5DB] text-[#4B5563] hover:border-[#9CA3AF]'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {loading ? (
              <div className="space-y-4 animate-pulse">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="bg-white border border-[#E5E7EB] rounded-md shadow-sm overflow-hidden p-5">
                    <div className="h-6 bg-[#E5E7EB] rounded w-2/3 mb-4"></div>
                    <div className="space-y-3">
                      <div className="h-4 bg-[#F3F4F6] rounded w-full"></div>
                      <div className="h-4 bg-[#F3F4F6] rounded w-5/6"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredResults.length === 0 ? (
              <div className="text-center py-12 bg-white border border-[#E5E7EB] rounded-md">
                <Search className="mx-auto h-8 w-8 text-[#D1D5DB] mb-3" />
                <p className="text-[#374151] font-medium">Ничего не найдено</p>
                <p className="text-[#6B7280] text-sm mt-1">Попробуйте изменить параметры запроса</p>
              </div>
            ) : (
              filteredResults.map((item) => (
                <div key={item.service_id || item.name} className="bg-white border border-[#E5E7EB] rounded-md shadow-sm overflow-hidden animate-in fade-in duration-200">
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
                      const isExpanded = expandedHistory === `${item.service_id}_${priceItem.partner_id}`;
                      
                      return (
                        <div key={pIndex} className="flex flex-col">
                          <div className="p-5 flex justify-between items-center hover:bg-[#F9FAFB] transition-colors">
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
                            <div className="flex items-center gap-4">
                              <button 
                                onClick={() => toggleHistory(item.service_id, priceItem.partner_id, priceItem.original_name)}
                                className={`p-1.5 rounded-md border text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                                  isExpanded 
                                    ? 'bg-[#2563EB] border-[#2563EB] text-white' 
                                    : 'bg-white border-[#D1D5DB] text-[#4B5563] hover:bg-[#F9FAFB] hover:text-[#111827]'
                                }`}
                                title="Посмотреть динамику цены"
                              >
                                <TrendingUp size={13} />
                                <span>Динамика</span>
                              </button>
                              <div className="flex flex-col items-end min-w-[90px]">
                                <div className="text-base font-bold text-[#111827]">
                                  {displayPrice ? `${Number(displayPrice).toLocaleString('ru-RU')} ₸` : 'По запросу'}
                                </div>
                                {hasForeignCurrency && (
                                  <div className="text-[10px] text-[#9CA3AF]">
                                    (~ {Number(priceItem.price_original).toLocaleString('ru-RU')} {priceItem.currency_original})
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                          {isExpanded && (
                            <div className="px-5 pb-5">
                              {renderHistoryChart(historyData)}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
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
                          {p.currency_original !== 'KZT' ? `(~ ${p.price_original} ${p.currency_original})` : '-'}
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

      {/* Floating Chatbot Toggle Button */}
      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={() => setIsChatOpen(!isChatOpen)}
          className="bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] hover:scale-105 active:scale-95 text-white p-4 rounded-full shadow-2xl flex items-center justify-center transition-all cursor-pointer border border-[#3B82F6] font-semibold"
        >
          {isChatOpen ? <X size={20} /> : (
            <div className="flex items-center gap-2">
              <span>🩺 ИИ-Ассистент</span>
            </div>
          )}
        </button>
      </div>

      {/* Floating Chat Panel */}
      {isChatOpen && (
        <div className="fixed bottom-24 right-6 z-40 w-[420px] h-[550px] bg-white/95 backdrop-blur-md rounded-xl shadow-2xl border border-[#E5E7EB] flex flex-col overflow-hidden animate-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] p-4 text-white flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-[#10B981] rounded-full animate-ping"></div>
              <div>
                <h3 className="font-bold text-sm">ИИ-Ассистент MedPartners</h3>
                <span className="text-[10px] text-blue-100">В сети • Помощник по услугам</span>
              </div>
            </div>
            <button onClick={() => setIsChatOpen(false)} className="text-white/80 hover:text-white transition-colors cursor-pointer">
              <X size={18} />
            </button>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-[#F9FAFB]/50">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                {/* Bubble */}
                <div
                  className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-[#2563EB] text-white rounded-br-none'
                      : 'bg-white text-[#374151] border border-[#E5E7EB] rounded-bl-none shadow-sm'
                  }`}
                >
                  {msg.sender === 'bot' ? formatBotText(msg.text) : msg.text}
                </div>

                {/* Inline services results (if any) */}
                {msg.sender === 'bot' && msg.services && msg.services.length > 0 && (
                  <div className="mt-2 w-full space-y-2">
                    <div className="text-[10px] font-semibold text-[#4B5563] uppercase tracking-wider pl-1 mb-1">Найденные цены в клиниках:</div>
                    {msg.services.slice(0, 3).map((srv) => (
                      <div key={srv.service_id || srv.name} className="bg-white border border-[#E5E7EB] rounded-lg p-3 shadow-sm flex flex-col gap-2">
                        <div className="flex justify-between items-start">
                          <span className="font-bold text-[11px] text-[#111827] line-clamp-1">{srv.name}</span>
                          <span className="bg-[#EFF6FF] text-[#1D4ED8] px-1.5 py-0.2 rounded text-[9px] font-medium shrink-0">
                            {srv.specialty || 'Общая'}
                          </span>
                        </div>
                        <div className="divide-y divide-[#F3F4F6]">
                          {srv.prices.slice(0, 2).map((pr, pIdx) => {
                            const price = isResident ? pr.price_resident : pr.price_nonresident;
                            return (
                              <div key={pIdx} className="py-1 flex justify-between items-center text-[10px]">
                                <button 
                                  onClick={() => {
                                    setIsChatOpen(false);
                                    openPartnerModal(pr.partner_id);
                                  }}
                                  className="text-left font-medium text-[#2563EB] hover:underline truncate max-w-[140px]"
                                >
                                  {pr.partner_name}
                                </button>
                                <span className="font-bold text-[#111827]">{price ? `${Number(price).toLocaleString('ru-RU')} ₸` : 'По запросу'}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {chatLoading && (
              <div className="flex items-center gap-2 bg-white border border-[#E5E7EB] w-fit p-3 rounded-lg rounded-bl-none shadow-sm text-xs text-[#6B7280]">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#2563EB]" />
                <span>ИИ анализирует ваши симптомы и ищет прайсы...</span>
              </div>
            )}
          </div>

          {/* Input Form */}
          <form onSubmit={handleChatSubmit} className="p-3 border-t border-[#E5E7EB] bg-white flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Опишите симптомы..."
              className="flex-1 px-3 py-2 border border-[#D1D5DB] rounded-md text-xs bg-white text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB]"
              disabled={chatLoading}
            />
            <button
              type="submit"
              disabled={chatLoading || !chatInput.trim()}
              className="bg-[#2563EB] text-white px-3 py-2 rounded-md text-xs font-semibold hover:bg-[#1D4ED8] transition-colors disabled:opacity-50 cursor-pointer"
            >
              Отправить
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
