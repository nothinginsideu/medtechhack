import React from 'react';
import { CheckCircle2, AlertTriangle, FileText, Activity } from 'lucide-react';

export default function AdminDashboard() {
  // Mock data for MVP
  const anomalies = [
    {
      id: 1,
      raw_name: "Анализ крови общ. с фор-лой",
      suggested_name: "Общий анализ крови (ОАК)",
      confidence: 89,
      old_price: 1500,
      new_price: 3200,
      diff: "+113%",
      status: "anomaly"
    },
    {
      id: 2,
      raw_name: "УЗ-исследование брюшной полости",
      suggested_name: "УЗИ брюшной полости",
      confidence: 94,
      old_price: 5000,
      new_price: 5500,
      diff: "+10%",
      status: "ok"
    }
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-[#111827]">Панель оператора</h1>
        <p className="text-[#6B7280] mt-1">Аналитика, верификация парсинга и управление справочником</p>
      </div>

      {/* Dashboard Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <FileText size={20} />
            <h3 className="font-medium">Обработано прайсов</h3>
          </div>
          <div className="text-3xl font-bold text-[#111827]">124</div>
        </div>
        
        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <CheckCircle2 size={20} />
            <h3 className="font-medium">Автонормализация</h3>
          </div>
          <div className="flex items-end gap-2">
            <div className="text-3xl font-bold text-[#059669]">82%</div>
            <span className="text-sm text-[#6B7280] mb-1">цель: 70%</span>
          </div>
          <div className="w-full bg-[#E5E7EB] h-2 rounded-full mt-3 overflow-hidden">
            <div className="bg-[#059669] h-full rounded-full" style={{ width: '82%' }}></div>
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <AlertTriangle size={20} />
            <h3 className="font-medium">В очереди (Аномалии)</h3>
          </div>
          <div className="text-3xl font-bold text-[#DC2626]">18</div>
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 text-[#6B7280] mb-2">
            <Activity size={20} />
            <h3 className="font-medium">Активных клиник</h3>
          </div>
          <div className="text-3xl font-bold text-[#111827]">42</div>
        </div>
      </div>

      {/* Verification Queue (Split Screen) */}
      <div>
        <h2 className="text-xl font-bold text-[#111827] mb-4">Очередь верификации (AI Matching)</h2>
        <div className="space-y-4">
          {anomalies.map((item) => (
            <div 
              key={item.id} 
              className={`border rounded-xl overflow-hidden shadow-sm ${item.status === 'anomaly' ? 'border-[#FDE047] bg-[#FEFCE8]' : 'border-[#E5E7EB] bg-white'}`}
            >
              {item.status === 'anomaly' && (
                <div className="bg-[#FEFCE8] border-b border-[#FDE047] px-6 py-2 text-sm text-[#CA8A04] font-medium flex items-center gap-2">
                  <AlertTriangle size={16} />
                  Аномальное изменение цены! Требуется ручной аппрув.
                </div>
              )}
              
              <div className="flex flex-col lg:flex-row">
                {/* Source Block */}
                <div className="flex-1 p-6 border-b lg:border-b-0 lg:border-r border-[#E5E7EB]">
                  <div className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">Источник (Сырые данные)</div>
                  <div className="font-medium text-[#111827] text-lg mb-2">{item.raw_name}</div>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="text-[#6B7280]">Старая цена: <span className="line-through">{item.old_price} ₸</span></div>
                    <div className="text-[#111827] font-semibold">Новая цена: {item.new_price} ₸</div>
                    <div className={`font-bold ${item.status === 'anomaly' ? 'text-[#DC2626]' : 'text-[#6B7280]'}`}>
                      ({item.diff})
                    </div>
                  </div>
                </div>

                {/* AI Suggestion Block */}
                <div className="flex-1 p-6 bg-white">
                  <div className="flex justify-between items-start mb-3">
                    <div className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Предложение ИИ</div>
                    <div className="bg-[#ECFDF5] text-[#059669] px-2 py-0.5 rounded text-xs font-medium">
                      Уверенность: {item.confidence}%
                    </div>
                  </div>
                  <div className="font-medium text-[#1D4ED8] text-lg mb-4">{item.suggested_name}</div>
                  
                  <div className="flex gap-3 mt-auto">
                    <button className="flex-1 bg-[#10B981] hover:bg-[#059669] text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
                      Подтвердить связь
                    </button>
                    <button className="flex-1 bg-white border border-[#D1D5DB] hover:bg-[#F9FAFB] text-[#374151] px-4 py-2 rounded-md text-sm font-medium transition-colors">
                      Выбрать вручную
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
