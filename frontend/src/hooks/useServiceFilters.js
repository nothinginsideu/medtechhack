import { useState, useMemo, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

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
  const [categories, setCategories] = useState(['Все']);

  const debouncedQuery = useDebounce(query, 300);

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
        const response = await axios.get(`${API_BASE_URL}/api/v1/search?q=${encodeURIComponent(trimmedQuery)}`);
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

  // First pass: filter by city and build dynamic categories
  const { cityFilteredResults, dynamicCategories } = useMemo(() => {
    const specs = new Set();
    
    const cityFiltered = results.map(service => {
      const filteredPrices = service.prices.filter(price => {
        const matchesCity = !selectedCity || price.partner_city === selectedCity;
        return matchesCity;
      });
      
      const sortedPrices = [...filteredPrices].sort((a, b) => {
        const valA = isResident ? (a.price_resident ?? Infinity) : (a.price_nonresident ?? Infinity);
        const valB = isResident ? (b.price_resident ?? Infinity) : (b.price_nonresident ?? Infinity);
        return valA - valB;
      });

      if (sortedPrices.length > 0) {
        specs.add(service.specialty || 'Общая');
      }

      return {
        ...service,
        prices: sortedPrices
      };
    }).filter(service => service.prices.length > 0);
    
    return {
      cityFilteredResults: cityFiltered,
      dynamicCategories: ['Все', ...Array.from(specs).sort()]
    };
  }, [results, selectedCity, isResident]);

  // Second pass: filter by active category
  const filteredResults = useMemo(() => {
    // If the active category is no longer valid, reset to 'Все' (handled in component usually, but safe here)
    if (activeCategory !== 'Все' && !dynamicCategories.includes(activeCategory)) {
      setActiveCategory('Все');
    }
    
    return cityFilteredResults.filter(service => {
      if (activeCategory === 'Все') return true;
      return (service.specialty || 'Общая') === activeCategory;
    });
  }, [cityFilteredResults, activeCategory, dynamicCategories]);

  return {
    query,
    setQuery,
    activeCategory,
    setActiveCategory,
    isResident,
    setIsResident,
    loading,
    searched,
    filteredResults,
    categories: dynamicCategories
  };
}
