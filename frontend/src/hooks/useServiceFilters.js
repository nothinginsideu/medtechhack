import { useState, useMemo, useEffect } from 'react';
import axios from 'axios';

// Debounce hook helper
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function useServiceFilters(initialResults = [], selectedCity = 'Астана') {
  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('Все');
  const [isResident, setIsResident] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(initialResults);
  const [searched, setSearched] = useState(false);

  const debouncedQuery = useDebounce(query, 300);

  // Helper to map 122 database specialties to 4 main categories
  const getCategoryForSpecialty = (specialty) => {
    if (!specialty) return 'Консультации';
    const spec = specialty.trim();

    // 1. Лаборатория (Laboratory)
    const labSpecialties = [
      'ИФА', 'Биохимия', 'Коагулология', 'ПЦР', 'Общая клиника',
      'Серология', 'ИХЛ', 'Гематология', 'Гистология',
      'Иммуногистохимия', 'Иммунофенотипирование', 'Цитогенетика',
      'РИФ', 'Иммуноцитология', 'Радиоиммунология', 'Молекулярная генетика'
    ];
    if (labSpecialties.includes(spec)) {
      return 'Лаборатория';
    }

    // 2. Диагностика (Diagnostics)
    const diagSpecialties = [
      'УЗИ', 'Рентген', 'КТ', 'МРТ', 'Эндоскпия', 'Эндоскопия',
      'Функциональная диагностика', 'Check-Up', 'Профосмотр'
    ];
    if (diagSpecialties.includes(spec)) {
      return 'Диагностика';
    }

    // 3. Процедуры (Procedures)
    const procSpecialties = [
      'Массаж', 'Физиотерапевт', 'Медсестра', 'Дневной стационар',
      'Стационарное лечение', 'Санаторно-курортное лечение', 'Вакцинация',
      'Медикаменты', 'Инструктор ЛФК', 'Кинезиотерапевт',
      'Рефлексотерапевт', 'Скорая помощь и транспортировка', 'Услуги зарубежом',
      'Беременность и роды', 'Реабилитолог', 'Мануальный терапевт', 'Остеопат',
      'Подолог', 'Справки'
    ];
    if (procSpecialties.includes(spec)) {
      return 'Процедуры';
    }

    // 4. Консультации (Consultations)
    return 'Консультации';
  };

  // Fetch results when debounced query changes
  useEffect(() => {
    const fetchResults = async () => {
      const trimmedQuery = debouncedQuery.trim();
      if (trimmedQuery.length < 2) {
        setResults([]);
        setSearched(false);
        return;
      }

      setLoading(true);
      setSearched(true);
      try {
        const response = await axios.get(`http://localhost:8000/api/v1/search?q=${encodeURIComponent(trimmedQuery)}`);
        setResults(response.data);
      } catch (error) {
        console.error("Error fetching services:", error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [debouncedQuery]);

  // Combined client-side filtering via useMemo (logical AND)
  const filteredResults = useMemo(() => {
    const searchLower = query.toLowerCase().trim();

    return results
      .map(service => {
        // Filter prices within each service by the selected city
        const filteredPrices = service.prices.filter(price => {
          // Filter by selected city
          const matchesCity = !selectedCity || price.partner_city === selectedCity;
          if (!matchesCity) return false;

          // If user searched for a specific clinic name or service words, check if all words match
          if (searchLower.length >= 2) {
            const queryWords = searchLower.split(/[\s,.-]+/).filter(w => w.length >= 2);
            if (queryWords.length > 0) {
              const matchesAllWords = queryWords.every(word => {
                const matchesClinic = price.partner_name.toLowerCase().includes(word);
                const matchesService = service.name.toLowerCase().includes(word);
                const matchesSpec = (service.specialty || '').toLowerCase().includes(word);
                const matchesOriginal = (price.original_name || '').toLowerCase().includes(word);
                return matchesClinic || matchesService || matchesSpec || matchesOriginal;
              });
              
              if (!matchesAllWords) {
                return false;
              }
            }
          }

          return true;
        });

        // Dynamic sorting based on resident status
        const sortedPrices = [...filteredPrices].sort((a, b) => {
          const valA = isResident ? (a.price_resident ?? Infinity) : (a.price_nonresident ?? Infinity);
          const valB = isResident ? (b.price_resident ?? Infinity) : (b.price_nonresident ?? Infinity);
          return valA - valB;
        });

        return {
          ...service,
          prices: sortedPrices
        };
      })
      // Keep only services that have prices available in the selected city
      .filter(service => service.prices.length > 0)
      // Filter by category tab
      .filter(service => {
        if (activeCategory === 'Все') return true;
        return getCategoryForSpecialty(service.specialty) === activeCategory;
      });
  }, [results, query, activeCategory, selectedCity, isResident]);

  return {
    query,
    setQuery,
    activeCategory,
    setActiveCategory,
    isResident,
    setIsResident,
    loading,
    searched,
    filteredResults
  };
}
