# -*- coding: utf-8 -*-
import six
from ._collections import PVLGroup, Units
from ._strings import needs_quotes, quote_string


class PVLEncoder(object):
    group = b'BEGIN_GROUP'
    end_group = b'END_GROUP'
    object = b'BEGIN_OBJECT'
    end_object = b'END_OBJECT'
    end_statement = b'END'
    null = b'NULL'
    true = b'TRUE'
    false = b'FALSE'
    assignment = b' = '
    indentation = b'  '
    newline = b'\n'

    def indent(self, level, stream):
        stream.write(level * self.indentation)

    def encode(self, module, stream):
        self.encode_block(module, 0, stream)
        stream.write(self.end_statement)

    def encode_block(self, block, level, stream):
        for key, value in six.iteritems(block):
            self.encode_statement(key, value, level, stream)

    def encode_statement(self, key, value, level, stream):
        if isinstance(value, PVLGroup):
            return self.encode_group(key, value, level, stream)

        if isinstance(value, dict):
            return self.encode_object(key, value, level, stream)

        self.encode_assignment(key, value, level, stream)

    def encode_group(self, key, value, level, stream):
        self.encode_group_begin(key, value, level, stream)
        self.encode_block(value, level + 1, stream)
        self.encode_group_end(key, value, level, stream)

    def encode_group_begin(self, key, value, level, stream):
        self.encode_raw_assignment(
            key=self.group,
            value=key.encode('utf-8'),
            level=level,
            stream=stream
        )

    def encode_group_end(self, key, value, level, stream):
        self.encode_raw_assignment(
            key=self.end_group,
            value=key.encode('utf-8'),
            level=level,
            stream=stream
        )

    def encode_object(self, key, value, level, stream):
        self.encode_object_begin(key, value, level, stream)
        self.encode_block(value, level + 1, stream)
        self.encode_object_end(key, value, level, stream)

    def encode_object_begin(self, key, value, level, stream):
        self.encode_raw_assignment(
            key=self.object,
            value=key.encode('utf-8'),
            level=level,
            stream=stream
        )

    def encode_object_end(self, key, value, level, stream):
        self.encode_raw_assignment(
            key=self.end_object,
            value=key.encode('utf-8'),
            level=level,
            stream=stream
        )

    def encode_assignment(self, key, value, level, stream):
        self.encode_raw_assignment(
            key=key.encode('utf-8'),
            value=self.encode_value(value),
            level=level,
            stream=stream
        )

    def encode_raw_assignment(self, key, value, level, stream):
        self.indent(level, stream)
        stream.write(key)
        stream.write(self.assignment)
        stream.write(value)
        stream.write(self.newline)

    def encode_value(self, value):
        if isinstance(value, Units):
            units = self.encode_units(value.units)
            value = self.encode_simple_value(value.value)
            return value + b' ' + units
        return self.encode_simple_value(value)

    def encode_simple_value(self, value):
        if isinstance(value, six.string_types):
            return self.encode_string(value)

        if isinstance(value, (int, float)):
            return self.encode_number(value)

        if value is None:
            return self.encode_null(value)

        if isinstance(value, bool):
            return self.encode_bool(value)

        if isinstance(value, list):
            return self.encode_list(value)

        if isinstance(value, set):
            return self.encode_set(value)

        return self.default(value)

    def encode_units(self, value):
        return b'<' + value.encode('utf-8') + b'>'

    def encode_null(self, value):
        return self.null

    def encode_number(self, value):
        return str(value).encode('utf-8')

    def encode_string(self, value):
        if needs_quotes(value):
            return quote_string(value)
        return value.encode('utf-8')

    def encode_bool(self, value):
        if value:
            return self.true
        return self.false

    def encode_sequence(self, values):
        return b', '.join([self.encode_value(v) for v in values])

    def encode_list(self, value):
        return b'(' + self.encode_sequence(value) + b')'

    def encode_set(self, value):
        return b'{' + self.encode_sequence(value) + b'}'

    def default(self, value):
        raise TypeError(repr(value) + " is not serializable")


class IsisCubeLabelEncoder(PVLEncoder):
    group = b'Group'
    end_group = b'End_Group'
    object = b'Object'
    end_object = b'End_Object'
    end_statement = b'End'

    def encode_group_end(self, key, value, level, stream):
        self.indent(level, stream)
        stream.write(self.end_group)
        stream.write(self.newline)

    def encode_object_end(self, key, value, level, stream):
        self.indent(level, stream)
        stream.write(self.end_object)
        stream.write(self.newline)


class PDSLabelEncoder(PVLEncoder):
    group = b'GROUP'
    end_group = b'END'
    object = b'OBJECT'
    end_object = b'END'
    end_statement = b'END'

    def _detect_assignment_col(self, block, indent=0):
        block_items = six.iteritems(block)
        return max(self._key_length(k, v, indent) for k, v in block_items)

    def _key_length(self, key, value, indent):
        length = indent + len(key)

        if isinstance(value, dict):
            indent += len(self.indentation)
            return max(length, self._detect_assignment_col(value, indent))

        return length

    def encode(self, module, stream):
        self.assignment_col = self._detect_assignment_col(module)
        super(PDSLabelEncoder, self).encode(module, stream)

    def encode_raw_assignment(self, key, value, level, stream):
        indented_key = (level * self.indentation) + key
        stream.write(indented_key.ljust(self.assignment_col))
        stream.write(self.assignment)
        stream.write(value)
        stream.write(self.newline)
