import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Search, Loader2, TrendingUp, X, MapPin, Building2, Phone, ShieldCheck } from 'lucide-react';
import { useServiceFilters } from '../hooks/useServiceFilters';
import { API_BASE_URL } from '../config';

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
    filteredResults,
    categories
  } = useServiceFilters([], selectedCity);
  
  const [selectedPartner, setSelectedPartner] = useState(null);

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
  
  const chatContainerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const isUserScrolledUp = useRef(false);

  const formatPrice = (value) => {
    if (value === null || value === undefined || value === '') return 'Не указано';
    return `${Number(value).toLocaleString('ru-RU')} ₸`;
  };

  useEffect(() => {
    if (!isUserScrolledUp.current && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, chatLoading]);

  const handleChatScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    isUserScrolledUp.current = scrollHeight - scrollTop - clientHeight > 50;
  };

  const toggleHistory = async (serviceId, partnerId, rawName) => {
    const key = `${serviceId}_${partnerId}_${rawName}`;
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
      const response = await axios.get(`${API_BASE_URL}/api/v1/partners/${partnerId}/history?${params.toString()}`);
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
    isUserScrolledUp.current = false;
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/search/assistant`, {
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
      const errorMsg = error.response?.data?.detail || 'ИИ-Ассистент временно недоступен. Пожалуйста, попробуйте позже.';
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: errorMsg,
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
        <div className="flex items-center gap-2 text-xs text-[#6B7280] p-3 bg-[#F9FAFB] border border-[#E5E7EB] mt-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Загрузка истории изменений...
        </div>
      );
    }
    if (!data || data.length === 0) {
      return (
        <div className="text-xs text-[#6B7280] p-3 bg-[#F9FAFB] border border-[#E5E7EB] mt-2">
          Нет исторических данных об изменениях цены для этой услуги в клинике.
        </div>
      );
    }
    if (data.length === 1) {
      const p = isResident ? data[0].price : data[0].price_nonresident;
      return (
        <div className="flex gap-4 items-center text-xs text-[#4B5563] p-3 bg-[#F9FAFB] border border-[#E5E7EB] mt-2">
          <span>Период действия цены ({data[0].date}):</span>
          <span className="font-semibold text-[#111827]">{formatPrice(p)}</span>
          <span className="text-[#9CA3AF]">(Только одна точка цены в базе)</span>
        </div>
      );
    }
    
    const width = 300;
    const height = 80;
    const padding = 15;
    
    const chartRows = data.filter(d => {
      const value = isResident ? d.price : d.price_nonresident;
      return value !== null && value !== undefined;
    });
    const prices = chartRows.map(d => isResident ? d.price : d.price_nonresident);
    if (prices.length === 0) {
      return (
        <div className="text-xs text-[#6B7280] p-3 bg-[#F9FAFB] border border-[#E5E7EB] mt-2">
          Для выбранного тарифа отдельная цена не указана.
        </div>
      );
    }
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;
    
    const points = chartRows.map((d, index) => {
      const x = padding + (index / (chartRows.length - 1 || 1)) * (width - 2 * padding);
      const currentPrice = isResident ? d.price : d.price_nonresident;
      const y = height - padding - ((currentPrice - minPrice) / priceRange) * (height - 2 * padding);
      return { x, y, label: formatPrice(currentPrice), date: d.date.substring(5) };
    });
    
    const polylinePoints = points.map(p => `${p.x},${p.y}`).join(' ');
    
    return (
      <div className="flex flex-col gap-2 mt-2 bg-[#F9FAFB] p-3 border border-[#E5E7EB] w-full">
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
            {chartRows.map((d, idx) => {
              const p = isResident ? d.price : d.price_nonresident;
              return (
                <div key={idx} className="flex justify-between items-center text-[10px] text-[#4B5563]">
                  <span>{d.date}</span>
                  <span className="font-semibold text-[#111827]">{formatPrice(p)}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };



  const openPartnerModal = async (partnerId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/partner/${partnerId}`);
      setSelectedPartner(response.data);
    } catch (error) {
      console.error("Ошибка загрузки профиля клиники:", error);
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
              className="block w-full pl-10 pr-4 py-3 border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB] transition-"
              placeholder="Введите название услуги..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="absolute inset-y-0 right-1.5 flex items-center">
              <button 
                type="submit" 
                disabled={loading}
                className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-5 py-1.5 text-sm font-medium"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Найти'}
              </button>
            </div>
          </form>

          {/* Toggle Resident */}
          <div className="flex items-center bg-[#F3F4F6] border border-[#E5E7EB] p-1 shrink-0">
            <button 
              onClick={() => setIsResident(true)}
              className={`px-3 py-1.5 text-sm font-medium ${isResident ? 'bg-white text-[#111827] ' : 'text-[#6B7280] hover:text-[#111827]'}`}
            >
              Резидент
            </button>
            <button 
              onClick={() => setIsResident(false)}
              className={`px-3 py-1.5 text-sm font-medium ${!isResident ? 'bg-white text-[#111827] ' : 'text-[#6B7280] hover:text-[#111827]'}`}
            >
              Нерезидент
            </button>
          </div>
        </div>
      </div>

      {!searched && (
        <div className="flex flex-col items-center mt-12 bg-white border border-[#E5E7EB] p-8">
          <TrendingUp className="h-8 w-8 text-[#2563EB] mb-3" />
          <h2 className="text-base font-semibold text-[#111827] mb-1">Быстрый поиск</h2>
          <p className="text-sm text-[#6B7280] mb-6 text-center">Выберите одну из популярных услуг, чтобы сравнить цены</p>
          
          <div className="flex flex-wrap gap-2 justify-center max-w-lg">
            {[
              { label: 'Анализ крови', query: 'кровь' },
              { label: 'Прием терапевта', query: 'терапевт' },
              { label: 'Консультация', query: 'консультация' },
              { label: 'УЗИ', query: 'УЗИ' },
              { label: 'ЭКГ', query: 'ЭКГ' },
              { label: 'Справка', query: 'справка' }
            ].map((item) => (
              <button
                key={item.label}
                onClick={() => setQuery(item.query)}
                className="px-4 py-2 bg-[#F3F4F6] hover:bg-[#E5E7EB] text-sm font-medium text-[#374151] flex items-center gap-1.5 cursor-pointer border border-[#E5E7EB]"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {searched && (
        <>
          {categories.length > 2 && (
            <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
              {categories.map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveCategory(tab)}
                  className={`px-3 py-1 text-xs font-medium whitespace-nowrap ${
   activeCategory === tab 
   ? 'bg-[#111827] text-white' 
   : 'bg-white border border-[#D1D5DB] text-[#4B5563] hover:border-[#9CA3AF]'
   }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          )}

          <div className="space-y-4">
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="bg-white border border-[#E5E7EB] overflow-hidden p-5">
                    <div className="h-6 bg-[#E5E7EB] w-2/3 mb-4"></div>
                    <div className="space-y-3">
                      <div className="h-4 bg-[#F3F4F6] w-full"></div>
                      <div className="h-4 bg-[#F3F4F6] w-5/6"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredResults.length === 0 ? (
              <div className="text-center py-12 bg-white border border-[#E5E7EB]">
                <Search className="mx-auto h-6 w-6 text-[#9CA3AF] mb-3" />
                <p className="text-[#6B7280] font-medium text-sm">Ничего не найдено</p>
                <p className="text-[#9CA3AF] text-xs mt-1">Проверьте правильность написания или попробуйте изменить фильтры</p>
              </div>
            ) : (
              filteredResults.map((item) => (
                <div key={item.service_id || item.name} className="bg-white border border-[#E5E7EB] overflow-hidden">
                  <div className="px-5 py-3 border-b border-[#E5E7EB] flex justify-between items-center bg-[#F9FAFB]">
                    <h2 className="text-base font-semibold text-[#111827]">{item.name}</h2>
                    <span className="bg-[#EFF6FF] text-[#1D4ED8] px-2.5 py-0.5 text-xs font-medium">
                      {item.specialty || 'Общая'}
                    </span>
                  </div>
                  <div className="divide-y divide-[#F3F4F6]">
                    {[...item.prices].sort((a, b) => {
                      const consRegex = /пробирк|игла|шприц|бабочк|контейнер|вакутайнер|система для|микротейнер|жгут|пластырь|перчатк|пеленк|бахил|шпател|зеркало|презерватив|гель|бинт|вата|салфетк|пинцет|маска|катетер|ланцет|скарификатор|скальпел|зонд|набор|расходн|материал/i;
                      const isConsA = consRegex.test(a.original_name);
                      const isConsB = consRegex.test(b.original_name);
                      if (isConsA && !isConsB) return 1;
                      if (!isConsA && isConsB) return -1;
                      return 0;
                    }).map((priceItem, pIndex) => {
                      const consRegex = /пробирк|игла|шприц|бабочк|контейнер|вакутайнер|система для|микротейнер|жгут|пластырь|перчатк|пеленк|бахил|шпател|зеркало|презерватив|гель|бинт|вата|салфетк|пинцет|маска|катетер|ланцет|скарификатор|скальпел|зонд|набор|расходн|материал/i;
                      const isConsumable = consRegex.test(priceItem.original_name);
                      
                      let displayPrice = priceItem.price_resident;
                      let isFallback = false;
                      if (!isResident) {
                        if (priceItem.price_nonresident !== null && priceItem.price_nonresident !== undefined && priceItem.price_nonresident !== "") {
                          displayPrice = priceItem.price_nonresident;
                        } else {
                          isFallback = true;
                        }
                      }
                      
                      const isExpanded = expandedHistory === `${item.service_id}_${priceItem.partner_id}_${priceItem.original_name}`;
                      
                      return (
                        <div key={pIndex} className="flex flex-col">
                          <div className={`p-5 flex justify-between items-center hover:bg-[#F9FAFB] ${isConsumable ? 'bg-[#FDFDFD] opacity-80' : ''}`}>
                            <div className="flex flex-col gap-1 w-2/3">
                              <button 
                                onClick={() => openPartnerModal(priceItem.partner_id)}
                                className="text-left font-medium text-[#2563EB] text-sm hover:underline hover:text-[#1D4ED8] flex items-center gap-1 w-fit"
                              >
                                <Building2 size={14} className="text-[#9CA3AF]"/>
                                {priceItem.partner_name}
                              </button>
                              <span className="text-xs text-[#6B7280]">По прайсу: {priceItem.original_name}</span>
                              <div className="flex gap-2 items-center mt-1">
                                <span className="text-[11px] font-medium text-[#059669] bg-[#ECFDF5] w-fit px-2 py-0.5">
                                  Актуально: {priceItem.date}
                                </span>
                                {priceItem.is_verified && (
                                  <span className="text-[#059669]" title="Верифицировано">
                                    <ShieldCheck size={14} />
                                  </span>
                                )}
                                {isConsumable && (
                                  <span className="text-[11px] font-medium text-[#6B7280] bg-[#F3F4F6] w-fit px-2 py-0.5 rounded border border-[#E5E7EB]">
                                    Расходный материал
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <button 
                                onClick={() => toggleHistory(item.service_id, priceItem.partner_id, priceItem.original_name)}
                                className={`p-1.5 border text-xs font-medium flex items-center gap-1.5 cursor-pointer ${
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
                                  {formatPrice(displayPrice)}
                                </div>
                                {isFallback && !isResident && (
                                  <div className="text-[10px] text-[#6B7280] bg-[#F3F4F6] px-1.5 py-0.5 mt-0.5 rounded">
                                    Единая цена
                                  </div>
                                )}
                                {priceItem.price_original !== undefined && priceItem.price_original !== null && (
                                  <div className="text-[10px] text-[#9CA3AF] mt-0.5">
                                    Исходная: {Number(priceItem.price_original).toLocaleString('ru-RU')} {priceItem.currency_original || 'KZT'}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex justify-between items-center p-5 border-b border-[#E5E7EB]">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-[#111827]">{selectedPartner.name}</h2>
                {selectedPartner.is_active && (
                  <div className="flex items-center gap-1.5 bg-[#ECFDF5] border border-[#A7F3D0] px-2 py-0.5 rounded-full" title="Актуальный прайс">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    <span className="text-[11px] text-[#059669] font-medium tracking-tight">
                      Актуально {selectedPartner.effective_date ? `до ${selectedPartner.effective_date}` : ''}
                    </span>
                  </div>
                )}
              </div>
              <button onClick={() => setSelectedPartner(null)} className="text-[#9CA3AF] hover:text-[#111827]">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-5 overflow-y-auto">
              <div className="grid grid-cols-2 gap-4 mb-6 bg-[#F9FAFB] p-4 border border-[#E5E7EB]">
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
              <div className="border border-[#E5E7EB] overflow-x-auto">
                <table className="w-full text-left text-sm whitespace-nowrap">
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
                        <td className="px-4 py-2 text-[#111827]">{formatPrice(p.price_resident)}</td>
                        <td className="px-4 py-2 text-[#6B7280]">{formatPrice(p.price_nonresident)}</td>
                        <td className="px-4 py-2 text-[#9CA3AF] text-xs">
                          {p.price_original !== undefined && p.price_original !== null ? `${Number(p.price_original).toLocaleString('ru-RU')} ${p.currency_original || 'KZT'}` : '-'}
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
          className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-5 py-3 flex items-center justify-center cursor-pointer font-medium text-sm border border-[#2563EB]"
        >
          {isChatOpen ? <X size={18} /> : (
            <div className="flex items-center gap-2">
              <span>Ассистент</span>
            </div>
          )}
        </button>
      </div>

      {/* Floating Chat Panel */}
      {isChatOpen && (
        <div className="fixed bottom-24 right-6 z-40 w-[420px] h-[550px] bg-white/95 border border-[#E5E7EB] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-[#2563EB] p-4 text-white flex justify-between items-center border-b border-[#E5E7EB]">
            <div className="flex items-center gap-2">
              
              <div>
                <h3 className="font-bold text-sm">ИИ-Ассистент MedPartners</h3>
                <span className="text-[10px] text-blue-100">В сети • Помощник по услугам</span>
              </div>
            </div>
            <button onClick={() => setIsChatOpen(false)} className="text-white/80 hover:text-white cursor-pointer">
              <X size={18} />
            </button>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-[#F9FAFB]/50" ref={chatContainerRef} onScroll={handleChatScroll}>
            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                {/* Bubble */}
                <div
                  className={`max-w-[85%] p-3 text-xs leading-relaxed ${
 msg.sender === 'user'
 ? 'bg-[#2563EB] text-white -br-none'
 : 'bg-white text-[#374151] border border-[#E5E7EB] -bl-none '
 }`}
                >
                  {msg.sender === 'bot' ? formatBotText(msg.text) : msg.text}
                </div>

                {/* Inline services results (if any) */}
                {msg.sender === 'bot' && msg.services && msg.services.length > 0 && (
                  <div className="mt-2 w-full space-y-2">
                    <div className="text-[10px] font-semibold text-[#4B5563] uppercase tracking-wider pl-1 mb-1">Найденные цены в клиниках:</div>
                    {msg.services.slice(0, 3).map((srv) => (
                      <div key={srv.service_id || srv.name} className="bg-white border border-[#E5E7EB] p-3 flex flex-col gap-2">
                        <div className="flex justify-between items-start">
                          <span className="font-bold text-[11px] text-[#111827] line-clamp-1">{srv.name}</span>
                          <span className="bg-[#EFF6FF] text-[#1D4ED8] px-1.5 py-0.2 text-[9px] font-medium shrink-0">
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
                                <span className="font-bold text-[#111827]">{formatPrice(price)}</span>
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
              <div className="flex items-center gap-2 bg-white border border-[#E5E7EB] w-fit p-3 -bl-none text-xs text-[#6B7280]">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#2563EB]" />
                <span>ИИ анализирует ваши симптомы и ищет прайсы...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleChatSubmit} className="p-3 border-t border-[#E5E7EB] bg-white flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Опишите симптомы..."
              className="flex-1 px-3 py-2 border border-[#D1D5DB] text-xs bg-white text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#2563EB] focus:border-[#2563EB]"
              disabled={chatLoading}
            />
            <button
              type="submit"
              disabled={chatLoading || !chatInput.trim()}
              className="bg-[#2563EB] text-white px-3 py-2 text-xs font-semibold hover:bg-[#1D4ED8] disabled:opacity-50 cursor-pointer"
            >
              Отправить
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
