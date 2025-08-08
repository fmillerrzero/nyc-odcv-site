// COMPREHENSIVE FIX for Google Places Autocomplete matching
// This replaces the filterTableWithValue function to handle ALL cases

function filterTableWithValue(searchValue) {
    const rows = document.querySelectorAll('#buildingTable tbody tr');
    let visibleCount = 0;
    
    if (!searchValue || searchValue.trim() === '') {
        // Show all if empty
        rows.forEach(row => {
            row.style.display = '';
            visibleCount++;
        });
    } else {
        // Prepare search term - lowercase and trimmed
        const originalSearch = searchValue.toLowerCase().trim();
        
        // Generate ALL possible variations
        const searchVariations = generateAllSearchVariations(originalSearch);
        
        // Check each row
        rows.forEach(row => {
            const rowData = (row.getAttribute('data-search') || '').toLowerCase();
            
            // Match if ANY variation works
            const matches = searchVariations.some(variation => {
                // Skip empty variations
                if (!variation || variation.length < 2) return false;
                
                // Direct substring match
                if (rowData.includes(variation)) return true;
                
                // Word-by-word matching for multi-word searches
                const words = variation.split(/\s+/).filter(w => w.length > 2);
                if (words.length > 1) {
                    // All significant words must be present
                    return words.every(word => rowData.includes(word));
                }
                
                return false;
            });
            
            row.style.display = matches ? '' : 'none';
            if (matches) visibleCount++;
        });
    }
    
    updateResultCounter(visibleCount);
    updateClearButtonState();
}

function generateAllSearchVariations(searchTerm) {
    const variations = new Set();
    
    // Always include original
    variations.add(searchTerm);
    
    // Remove ALL possible location suffixes that Google might add
    const locationSuffixes = [
        /, new york, ny.*$/i,
        /, ny.*$/i,
        /, new york.*$/i,
        /, usa.*$/i,
        /, united states.*$/i,
        /, manhattan.*$/i,
        /, nyc.*$/i,
        /, 10[0-9]{3}.*$/i  // Remove zip codes
    ];
    
    let cleanedSearch = searchTerm;
    locationSuffixes.forEach(pattern => {
        const cleaned = searchTerm.replace(pattern, '').trim();
        if (cleaned !== searchTerm) {
            variations.add(cleaned);
            cleanedSearch = cleaned;
        }
    });
    
    // Building type suffixes to try removing AND adding
    const buildingTypes = [
        'building', 'bldg', 'tower', 'plaza', 'place', 'center', 'centre',
        'square', 'sq', 'park', 'house', 'hall', 'court', 'gardens',
        'apartments', 'apts', 'hotel', 'offices', 'complex', 'station',
        'terrace', 'manor', 'residence', 'suites', 'lofts'
    ];
    
    // For each current variation, try removing building types
    Array.from(variations).forEach(variant => {
        buildingTypes.forEach(type => {
            // Remove from end
            if (variant.endsWith(' ' + type)) {
                variations.add(variant.slice(0, -(type.length + 1)));
            }
            // Remove from anywhere
            if (variant.includes(' ' + type + ' ') || variant.includes(' ' + type)) {
                variations.add(variant.replace(new RegExp('\\s+' + type + '\\b', 'gi'), '').trim());
            }
        });
    });
    
    // Try ADDING common types if not present (for partial names)
    const baseSearch = cleanedSearch.replace(/\s+(building|tower|square|plaza|center)$/i, '');
    if (!cleanedSearch.match(/\b(building|tower|square|plaza|center|sq)\b/i)) {
        variations.add(baseSearch + ' building');
        variations.add(baseSearch + ' tower');
        variations.add(baseSearch + ' square');
        variations.add(baseSearch + ' sq');
    }
    
    // Handle abbreviations and expansions
    const abbreviations = [
        ['square', 'sq'],
        ['building', 'bldg'],
        ['apartments', 'apts'],
        ['street', 'st'],
        ['avenue', 'ave'],
        ['boulevard', 'blvd'],
        ['place', 'pl'],
        ['court', 'ct'],
        ['terrace', 'ter'],
        ['drive', 'dr'],
        ['road', 'rd'],
        ['parkway', 'pkwy'],
        ['center', 'ctr'],
        ['&', 'and']
    ];
    
    Array.from(variations).forEach(variant => {
        abbreviations.forEach(([full, abbr]) => {
            // Try both directions
            if (variant.includes(full)) {
                variations.add(variant.replace(new RegExp('\\b' + full + '\\b', 'gi'), abbr));
            }
            if (variant.includes(abbr)) {
                variations.add(variant.replace(new RegExp('\\b' + abbr + '\\b', 'gi'), full));
            }
        });
    });
    
    // Handle number words
    const numberWords = [
        ['one', '1'], ['two', '2'], ['three', '3'], ['four', '4'], ['five', '5'],
        ['six', '6'], ['seven', '7'], ['eight', '8'], ['nine', '9'], ['ten', '10'],
        ['first', '1st'], ['second', '2nd'], ['third', '3rd'], ['fourth', '4th'],
        ['fifth', '5th'], ['sixth', '6th'], ['seventh', '7th'], ['eighth', '8th'],
        ['ninth', '9th'], ['tenth', '10th']
    ];
    
    Array.from(variations).forEach(variant => {
        numberWords.forEach(([word, num]) => {
            if (variant.includes(word)) {
                variations.add(variant.replace(new RegExp('\\b' + word + '\\b', 'gi'), num));
            }
            if (variant.includes(num)) {
                variations.add(variant.replace(new RegExp('\\b' + num + '\\b', 'gi'), word));
            }
        });
    });
    
    // Special NYC cases
    Array.from(variations).forEach(variant => {
        // 6th Avenue <-> Avenue of the Americas
        if (variant.includes('6th') || variant.includes('sixth')) {
            variations.add(variant.replace(/\b(6th|sixth)\s+(ave|avenue)\b/gi, 'ave of the americas'));
            variations.add(variant.replace(/\b(6th|sixth)\s+(ave|avenue)\b/gi, 'avenue of the americas'));
        }
        if (variant.includes('avenue of the americas') || variant.includes('ave of the americas')) {
            variations.add(variant.replace(/\b(avenue|ave)\s+of\s+the\s+americas\b/gi, '6th ave'));
            variations.add(variant.replace(/\b(avenue|ave)\s+of\s+the\s+americas\b/gi, '6th avenue'));
        }
        
        // Times Square special cases
        if (variant.includes('times')) {
            variations.add(variant.replace(/\btimes\s+square\b/gi, 'times sq'));
            variations.add(variant.replace(/\btimes\s+sq\b/gi, 'times square'));
        }
    });
    
    // Remove empty or too-short variations
    return Array.from(variations).filter(v => v && v.length >= 2);
}