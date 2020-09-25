# Madoc Search Service API

## POSTing data

The service accepts a JSON POSTrequest at `iiif/` with headers:

```json
{"Content-Type": "application/json", "Accept": "application/json"}
```

The payload format is:

```json
{
  "contexts": 
    [
       {
          "id": "urn:madoc:site:2", 
          "type": "Site"
        },
       {
          "id": "https://example.org/collections/foo",
          "type": "Collection"
         }
     ],
  "resource": { },
  "id": "urn:madoc:manifest:foo",
  "thumbnail": "http://madoc.foo/thumbnail/foo/fake.jpg"
}
```

* contexts: List of contexts with identifier and type
* resource: the JSON for the IIIF resource
* id: the identifier (in Madoc) for the resource
* thumbnail: URL for the thumbnail (in Madoc) for the resource

## Simple GET Query API

The search API is at `search/`. 

The basic query parameters are as follows


* `?fulltext=foo` : search against the preindexed fulltext (term vectors) for `foo`
* `?contexts__id=urn:madoc:site:2`: filter to just objects with that context (N.B. that's a double underscore)
* `?madoc_id=urn:madoc:manifest:saa-AA0428a`: filter to just hits within that one object (n.b. that's a single underscore)

In principle, we can add filters trivially easy for any other fields in the IIIF resource that make sense to filter on. 
They need to be added to a list of filterset_fields, but other than that, the code is already in place.

Querying for a facet:

* `?facet_type=metadata&facet_subtype=material&facet_value=paper&fulltext=Abbey`: filter the existing search results (for "Abbey") on metadata, where the metadata field "material" equals "paper"


# JSON Query API

The accepted fields are as follows:

* __fulltext__: _Optional_ This is the text you want to search for in the indexed fulltext.
* __search_language__: _Optional_ This is the language you want to use in constructing the query, this determines how the query parser will stem/parse the text that you provide in the 'fulltext' parameter.
* __search_type__: _Optional_ This is the type of search to use in constructing the query, e.g. 'websearch', 'plaintext', 'raw' - see https://docs.djangoproject.com/en/3.1/ref/contrib/postgres/search/#searchquery
* __type__: _Optional_ Search againsts just textual data with this type, e.g. metadata (to only search metadata)
* __subtype__: _Optional_ Search against just textual data with this subtype, e.g. a specific metadata field.
* __language_display__: _Optional_ only search fields where the display language is, e.g. "english".
* __language_iso639_1__: _Optional_ only search fields where the iso639_1 language code is, e.g. "en" 
* __language_iso639_2__: _Optional_ only search fields where the iso639_2 language code is, e.g. "eng" 
* __iiif_identifiers__: _Optional_ an array of identifiers (these should be the `@id`s for the objects), the query will filter to just these objects before it runs any fulltext or facet filters.
* __madoc_identifiers__: _Optional_ an array of identifiers (these should be the `madoc id`s for the objects), the query will filter to just these objects before it runs any fulltext or facet filters.
* __contexts__: _Optional_ an array of identifiers (these should be the ids for the relevant site, project, collection, etc), the query will filter to just those objects associated with those _any_ of those contexts before it runs any fulltext or facet filters.
* __facet_fields__: _Optional_ an array of strings which represent the fields which will have facet counts provided in the result output. These are assumed to be _labels_ in the resource _metadata_ (and otherwise have no semantics).
* __facets__: _Optional_ an array of facet queries (see below) which are applied as filters to the query output.

Facet queries have the following format:

* __type__: The indexed text type, e.g. "metadata" or "descriptive", etc
* __subtype__: The subtype, e.g. "place of publication", "label", etc.
* __value__: The value to match, e.g. "Berlin"
* __field_lookup__: _Optional_ The method to use when matching. This defaults to `iexact` (case insensitive exact match) but the query parser will accept any of the standard field_lookup types. N.B. this applies to all of type, subtype and value. See: https://docs.djangoproject.com/en/3.1/ref/models/querysets/#field-lookups

N.B. types and subtypes have no semantics, they are just organising labels applied to incoming content. The ingest code will default to storing all data from the IIIF metadata block with: type = "metadata" and subtype = the label for the field.

The query is constructed in the following order:

1. prefilter: filter the list of objects being queried against to just those objects:
   * associated with one or more of the _contexts_ if provided
   * whose madoc identifier is within the list of _madoc_identifiers_ if provided
   * whose IIIF `@id` is within the list of _iiif_identifiers_ if provided
2. fulltext query: search (using a PostgreSQL textsearch `tsquery`) the indexed content associated with all of the IIIF objects (this is currently IIIF descriptive properties and all metadata 'fields' but will include fulltext and capture models).
   * type: only search text marked with this `type`. Current types are `descriptive` (content in the IIIF manifest), `metadata` (content in the IIIF metadata block). Additional types will be added.
   * subtype: `field` type for the search text, e.g. `label` to search just the IIIF labels; `author` to search just metadata where the label is `author` etc.
   * language_display: only search fields where the display language is, e.g. "english".
   * language_iso639_1: only search fields where the iso639_1 language code is, e.g. "en" 
   * language_iso639_2: only search fields where the iso639_2 language code is, e.g. "eng" 
3. facet filter(s): apply the facet filters (which may be a mixture of ANDs and ORs, see examples below) to the result of the fulltext query.

Facet counts are calculated on the output of this query.


# Example 1

Fulltext search and a single facet.

## GET

[/api/search/search?fulltext=G%C3%B6tter&facet_type=metadata&facet_subtype=place%20of%20publication&facet_value=Hamburg&search_language=german](http://localhost:8000/api/search/search?fulltext=G%C3%B6tter&facet_type=metadata&facet_subtype=place%20of%20publication&facet_value=Hamburg&search_language=german)

In this example, we are searching for the _German_ plural of God, and faceting on objects where the metadata Place of Publication is Hamburg.

N.B. if we remove the `search_langauge=german` property, this will find zero hits, because although the test is indexed as German, the search query is not being stemmed/parsed using German fulltext rules.

## POST

POST to `/api/search/search`

```json
{
  "fulltext": "Götter",
  "search_language": "german",
  "contexts": [
    "urn:madoc:site:2"
  ],
  "facets": [
    {
      "type": "metadata",
      "subtype": "place of publication",
      "value": "Hamburg"
    }
  ]
}
```

In this example, we are also filtering to objects that appear in/are part of `urn:madoc:site:2`.

# Example 2

Fulltext search and multiple facets with specified facet fields.

```json
{
  "fulltext": "Abbey",
  "facet_fields": [
    "text language",
    "place of origin (english)",
    "collection name",
    "publisher",
    "persons",
    "material",
    "location"
  ],
  "contexts": [
    "urn:madoc:site:2"
  ],
  "facets": [
    {
      "type": "metadata",
      "subtype": "collection name",
      "value": "Staatsarchiv Aargau"
    },
    {
      "type": "metadata",
      "subtype": "material",
      "value": "paper"
    },
    {
      "type": "metadata",
      "subtype": "material",
      "value": "parchment"
    },
    {
      "type": "metadata",
      "subtype": "text language",
      "value": "German"
    }
  ]
}
```

In this instance we are searching for:

1. Fulltext = "Abbey"

AND

2. context = urn:madoc:site:2

AND 

3. Collection Name = Staatsarchiv Aargau

AND

4. Text Language = German

AND

5. Material = (Paper OR Parchment)

The query parser automatically combines any two queries against the _same_ field in the metadata as an _OR_, otherwise, all facets are applied as an _AND_.

Further, we are requesting that the results returned include the facet counts for:

```
    "text language",
    "place of origin (english)",
    "collection name",
    "publisher",
    "persons",
    "material",
    "location"
 ```
 
 If any of those fields don't exist on the query results, the system will return an empty object `{}` for that "field".
  
 The results returned in this case include a _facet_ key as follows
 
 ```json
 {
 ...
   "facets": {
    "metadata": {
      "text language": {
        "German": 10,
        "Latin": 4
      },
      "place of origin (english)": {
        "Königsfelden": 8,
        "Wettingen": 2
      },
      "collection name": {
        "Staatsarchiv Aargau": 10
      },
      "publisher": {},
      "persons": {
        "Author: Innocentius IV, Papa": 1,
        "Author: Rümlang, Eberhard von": 1,
        "Restorer: Gall, Ernst": 1,
        "Scribe: Peter, von Neumagen; Annotator: Tschudi, Aegidius": 1
      },
      "material": {
        "Paper": 9,
        "Parchment": 1
      },
      "location": {
        "Aarau": 10
      }
    }
  }
}
```

# Example 3

Filter by facet, without a fulltext search.

```json
{
  "facet_fields": [
    "text language",
    "place of origin (english)",
    "collection name",
    "publisher",
    "persons",
    "material",
    "location"
  ],
  "contexts": [
    "urn:madoc:site:2"
  ],
  "facets": [
    {
      "type": "metadata",
      "subtype": "collection name",
      "value": "Staatsarchiv Aargau"
    },
    {
      "type": "metadata",
      "subtype": "material",
      "value": "paper"
    },
    {
      "type": "metadata",
      "subtype": "material",
      "value": "parchment"
    },
    {
      "type": "metadata",
      "subtype": "text language",
      "value": "German"
    }
  ]
}
```

We can run the same query, but just set the facets and request the facet counts, without adding fulltext, e.g. the facet count this time:

```json
{
...
  "facets": {
    "metadata": {
      "text language": {
        "German": 13,
        "Latin": 6
      },
      "place of origin (english)": {
        "Königsfelden": 9,
        "Wettingen": 2,
        "Aarau": 1,
        "Southwestern Germany": 1
      },
      "collection name": {
        "Staatsarchiv Aargau": 13
      },
      "publisher": {},
      "persons": {
        "Author: Innocentius IV, Papa": 1,
        "Author: Rümlang, Eberhard von": 1,
        "Former possessor: Stettler, Anton": 1,
        "Restorer: Gall, Ernst": 1,
        "Scribe: Peter, von Neumagen; Annotator: Tschudi, Aegidius": 1
      },
      "material": {
        "Paper": 10,
        "Parchment": 3
      },
      "location": {
        "Aarau": 13
      }
    }
  }
}
```

# Example 4

```json
{
  "facet_fields": [
    "text language",
    "place of origin (english)",
    "collection name",
    "publisher",
    "persons",
    "material",
    "location"
  ],
  "contexts": [
    "urn:madoc:site:2"
  ],
  "facets": [
    {
      "type": "metadata",
      "subtype": "collection name",
      "value": "Staat",
      "field_lookup": "istartswith"
    },
    {
      "type": "metadata",
      "subtype": "material",
      "value": "paper"
    },
    {
      "type": "metadata",
      "subtype": "material",
      "value": "parchment"
    },
    {
      "type": "metadata",
      "subtype": "text language",
      "value": "German"
    }
  ]
}
```

As per Example 3, only this time we are using `istartswith` (case insensitive startswith) for the type = "metadata", subtype = "collection name", "value" = "Staat" facet. (N.B. this will also match, e.g. "collection name (English)" for example).