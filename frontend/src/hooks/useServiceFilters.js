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
  const [categories, setCategories] = useState(['Все']);

  const debouncedQuery = useDebounce(query, 300);

  // Fetch categories once on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/v1/categories');
        setCategories(['Все', ...response.data]);
      } catch (error) {
        console.error("Error fetching categories:", error);
      }
    };
    fetchCategories();
  }, []);

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
    return results
      .map(service => {
        // Filter prices within each service by the selected city
        const filteredPrices = service.prices.filter(price => {
          // Filter by selected city
          const matchesCity = !selectedCity || price.partner_city === selectedCity;
          if (!matchesCity) return false;

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
        // Direct match with DB specialty since we fetched them natively
        return (service.specialty || 'Консультации') === activeCategory;
      });
  }, [results, activeCategory, selectedCity, isResident]);

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
    categories
  };
}
