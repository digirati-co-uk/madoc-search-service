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


# Get a list of facets

POST to `/api/search/facets`

```json
{}
```

Will return a list of facets grouped by type for all contexts.

POST to `/api/search/facets`

```json
{"contexts":["https://iiif.ub.uni-leipzig.de/static/collections/Drucke17/collection.json"]}
```

Will return just the facet fields for objects within that list of contexts. 

The API accepts an optional list of facet types, e.g.

```json
{
"contexts":["https://iiif.ub.uni-leipzig.de/static/collections/Drucke17/collection.json"],
"facet_types":["metadata","descriptive"]}
```

The facets will be returned grouped by type, e.g.

```json
{
	"descriptive": ["attribution", "label"],
	"metadata": ["about", "alternate title", "attribution", "author", "author(s)", "call number", "century", "collection", "collection name", "comment", "date", "date added", "date of origin (english)", "date of publication", "dated", "description", "digitization project", "digitization sponsor", "digitized by", "dimensions", "disclaimers", "document type", "doi", "format", "full conditions of use", "full title", "holding institution", "katalogeintrag", "kitodo", "language", "liturgica christiana", "location", "manifest type", "material", "materials", "number of pages", "online since", "owner", "part of", "part reference", "persons", "physical description", "place of origin", "place of origin (english)", "place of publication", "provenance", "publication date", "publisher", "record created", "related", "repository", "rights/license", "series", "shelfmark", "source", "source ppn (swb)", "sponsored by", "summary", "summary (english)", "text language", "title", "title (english)", "topic", "urn", "vd16", "vd17"]
}
```
If no type is provided, the API will default to just `["metadata"]`.

# Autocomplete against a facet

This will provide a list of values for a specific facet field that can be used to populate an autocomplete and 
can be constrainted to a particular context.

Example 1:

All of the publishers starting with "g", for objects within a given context.

POST to `/api/search/autocomplete`


```json
{
  "contexts": [
    "https://iiif.ub.uni-leipzig.de/static/collections/Drucke17/collection.json"
  ],
  "autocomplete_type": "metadata",
  "autocomplete_subtype": "publisher",
  "autocomplete_query": "g"
}
```

# JSON Query API

The accepted fields are as follows:

* __fulltext__: _Optional_ This is the text you want to search for in the indexed fulltext.
* __search_language__: _Optional_ This is the language you want to use in constructing the query, this determines how the query parser will stem/parse the text that you provide in the 'fulltext' parameter.
* __search_type__: _Optional_ This is the type of search to use in constructing the query, e.g. 'websearch', 'plaintext', 'raw' - see https://docs.djangoproject.com/en/3.1/ref/contrib/postgres/search/#searchquery
* __type__: _Optional_ Search againsts just textual data with this type, e.g. metadata (to only search metadata)
* __subtype__: _Optional_ Search against just textual data with this subtype, e.g. a specific metadata field.
* __date_exact__: _Optional_ Search for just objects with a start and end date that exactly matches this
* __date_start__: _Optional_ Search for just objects with a start date that is great than or equal to
* __date_end__: _Optional_ Search for just objects with an end date less than or equal to
* __integer__: _Optional_ Search for an integer (this is an object with value and operator)
* __float__: _Optional_ Search for a float (this is an object with value and operator)
* __raw__: _Optional_ Provide an object with explicit "raw" query parameters.
* __language_display__: _Optional_ only search fields where the display language is, e.g. "english".
* __language_iso639_1__: _Optional_ only search fields where the iso639_1 language code is, e.g. "en" 
* __language_iso639_2__: _Optional_ only search fields where the iso639_2 language code is, e.g. "eng" 
* __iiif_identifiers__: _Optional_ an array of identifiers (these should be the `@id`s for the objects), the query will filter to just these objects before it runs any fulltext or facet filters.
* __madoc_identifiers__: _Optional_ an array of identifiers (these should be the `madoc id`s for the objects), the query will filter to just these objects before it runs any fulltext or facet filters.
* __contexts__: _Optional_ an array of identifiers (these should be the ids for the relevant site, project, collection, etc), the query will filter to just those objects associated with those _any_ of those contexts before it runs any fulltext or facet filters.
* __facet_fields__: _Optional_ an array of strings which represent the fields which will have facet counts provided in the result output. These are assumed to be _labels_ in the resource _metadata_ (and otherwise have no semantics).
* __facet_types__: _Optional_ an array of string which represent the type of the indexables the facets will be generated from. Defaults to ["metadata"] but, for example, if you also wanted to facet on fields in the IIIF descriptive properties, you could use ["metadata", "descriptive"]
* __facets__: _Optional_ an array of facet queries (see below) which are applied as filters to the query output.


Facet queries have the following format:

* __type__: The indexed text type, e.g. "metadata" or "descriptive", etc
* __subtype__: The subtype, e.g. "place of publication", "label", etc.
* __value__: The value to match, e.g. "Berlin" (N.B. this matches only against the `indexables` field)
* __field_lookup__: _Optional_ The method to use when matching. This defaults to `iexact` (case insensitive exact match) but the query parser will accept any of the standard field_lookup types. N.B. this applies to all of type, subtype and value. See: https://docs.djangoproject.com/en/3.1/ref/models/querysets/#field-lookups

Recently added, you can also facet against the `indexable_int` and `indexable_float` field (do not use `value` here).

e.g. 

```json
{
...
  "facets": [
    {
      "type": "metadata",
      "subtype": "place of publication",
      "value": "Hamburg"
    },
      {
      "type": "metadata",
      "subtype": "weight_in_kg",
      "indexable_int": 50,
      "field_lookup": "gte"
    }
  ]
}


N.B. types and subtypes have no semantics, they are just organising labels applied to incoming content. The ingest code will default to storing all data from the IIIF metadata block with: type = "metadata" and subtype = the label for the field.

Numeric queries (integers or floats) have the following format:

* __value__: the value to match
* __operator__: One of "exact", "lt", "gt", "lte", "gte"

e.g.

```json
{
  "integer": 
    {
       "value": 100,
        "operator": "gte"
    }
 }
```

Raw queries allow you to pass in standard Django filters as an object/dict. These __must__ target the indexables model.

THe general form is:

```json
{
	"raw": {
		"indexables__$FIELD__$FIELD_LOOKUP": "value"
	}
}
```

Where `$FIELD` is the field name in the Indexables model, and `$FIELDLOOKUP` corresponds to one of the standard
field lookup options in: [https://docs.djangoproject.com/en/3.1/ref/models/querysets/#field-lookups](https://docs.djangoproject.com/en/3.1/ref/models/querysets/#field-lookups)

For example:

```json
{
	"raw": {
		"indexables__subtype__iexact": "title",
        "indexables__original_content__icontains": "bible"
	}
}
```



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

# POSTing Capture models and OCR

POST to `/api/search/model`

```json
{
    "resource_id": "urn:foo:bar",
    "content_id": "123-abcdhd-24-j8-0000-foo",
    "resource": { ... the capture model or ocr data ...}
}
```

N.B. The following fields are compulsory:

* resource_id : the identifier in madoc for the object this relates to
* resource: there must be something to index

N.B. the _resource_id_ __must__ exist and must be already in the search service.

* content_id: 
    * for capture models (not the intermediate OCR format) the content_id used for each
        indexable object created will be derived _from the model_ and any content_id passed in in the POST will
        be ignored.
    * for OCR data, you MAY pass in a content_id and this will be used to identify the indexed content in the system,
        if not content_id is passed in, the system will generate one based on the resource_id and the content_type.


# POSTing "raw" Indexable content

POST to `/api/search/indexables`

```json
{
    "resource_id": "urn:foo:bar",
    "content_id": "https://example.org/foo/bar",
    "original_content": "<html>Whooo!</html>",
    "indexable": "Whooo!",
    "indexable_date": null,
    "indexable_int": null,
    "indexable_float": null,
    "indexable_json": null,
    "selector": null,
    "type": "custom",
    "subtype": "custom1",
    "language_iso639_2": "eng",
    "language_iso639_1": "en",
    "language_display": "english",
    "language_pg": "english"
}
```

N.B. The following fields are compulsory:

* resource_id : the identifier in madoc for the object this relates to
* indexable: this is the text to be indexed by the fulltext search
* original_content: this is whatever will get highlighted by the snipper API
* type: e.g. custom
* subtype: e.g. custom_subfield

N.B. the _resource_id_ __must__ exist and must be already in the search service.
