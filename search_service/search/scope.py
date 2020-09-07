import copy


def gen_key(context, separator):
    """
    Generate the key that
    :param context: list of config context elements, ordered from most specific to least specific
    :param separator: separator that should be used to generate the key
    :return:
    """
    if context and isinstance(context, list) and len(context) > 0:
        key = separator.join(context)
        return key
    return


def extend_keylist(keys, implicit_keys=None, append_implicit=False):
    """
    Extend a list of keys.

    :param keys:
    :param implicit_keys:
    :param append_implicit:
    :return:
    """
    w_keys = copy.deepcopy(keys)
    if implicit_keys and append_implicit:
        for k in implicit_keys:
            if len(w_keys) > 0:
                if w_keys[-1] != k:
                    w_keys.append(k)
            else:
                w_keys.append(k)
    return w_keys


def iterate_separated_keylist(keys, sep="|", extend_impl=True, implicit=None):
    """

    :param keys:
    :param sep:
    :param extend_impl
    :param implicit
    :return:
    """
    working_keys = copy.deepcopy(keys)
    if working_keys and isinstance(working_keys, list) and len(working_keys) > 0:
        keylist = extend_keylist(
            keys=working_keys, append_implicit=extend_impl, implicit_keys=implicit
        )
        keylist = iterate_keylist(keys=keylist)
        return [gen_key(context=x, separator=sep) for x in keylist]
    return


def iterate_keylist(keys):
    """
    Iterate a list of keys

    [a, b, c, d]

    Should return:

    a b c d

    b c d

    a c d

    c d

    a d

    d

    Or

    [a, b, c]

    Should return

    a b c
    b c
    a c
    c

    Or

    a b

    should return

    a b
    b


    :param keys: key list to iterate
    :return:
    """
    if keys:
        key_list = []
        length = len(keys)
        for x in range(0, length - 1):
            key_list.append([keys[0]] + keys[x + 1 :])
            key_list.append(keys[x + 1 :])
        return key_list
    return
