import React, { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Divider,
  Form,
  Input,
  Space,
  Typography,
} from 'antd';

const { Title, Paragraph, Text } = Typography;

const VERSION_MAP = {
  0b00110: 'v6',
  0b00101: 'v5',
  0b00100: 'v4',
  0b00011: 'v3',
  0b00010: 'v2',
};

const ALGORITHM_MAP = {
  0b000: 'HOTP',
  0b001: 'TOTP',
};

const OTP_LENGTH_MAP = {
  0b000: 6,
  0b001: 8,
};

const TYPE_MAP = {
  0b00: 'activation',
  0b01: 'transfer',
  0b10: 'reserve',
  0b11: 'reserve',
};

const PROTOCOL_MAP = {
  0b00: 'https',
  0b01: 'http',
};

const CHAR_MAP = {
  '000000': '0', '000001': '1', '000010': '2', '000011': '3',
  '000100': '4', '000101': '5', '000110': '6', '000111': '7',
  '001000': '8', '001001': '9', '001010': 'a', '001011': 'b',
  '001100': 'c', '001101': 'd', '001110': 'e', '001111': 'f',
  '010000': 'g', '010001': 'h', '010010': 'i', '010011': 'j',
  '010100': 'k', '010101': 'l', '010110': 'm', '010111': 'n',
  '011000': 'o', '011001': 'p', '011010': 'q', '011011': 'r',
  '011100': 's', '011101': 't', '011110': 'u', '011111': 'v',
  '100000': 'w', '100001': 'x', '100010': 'y', '100011': 'z',
  '100100': '.', '100101': '-', '111111': 'delimiter',
};

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

const base32Decode = (input) => {
  const normalized = input.toUpperCase().replace(/=+$/, '').replace(/\s+/g, '');
  if (!normalized) {
    throw new Error('Token is required.');
  }

  const bits = [];
  for (const char of normalized) {
    const index = BASE32_ALPHABET.indexOf(char);
    if (index === -1) {
      throw new Error('Token contains invalid base32 characters.');
    }
    bits.push(index.toString(2).padStart(5, '0'));
  }

  const bitString = bits.join('');
  const bytes = [];
  for (let i = 0; i + 8 <= bitString.length; i += 8) {
    bytes.push(parseInt(bitString.slice(i, i + 8), 2));
  }

  return Uint8Array.from(bytes);
};

const decodeToken = (token) => {
  const decoded = base32Decode(token);
  if (decoded.length < 40) {
    throw new Error('Decoded token is too short.');
  }

  const byte1 = decoded[0];
  const versionBits = (byte1 >> 3) & 0x1f;
  const algorithmBits = byte1 & 0x07;

  const version = VERSION_MAP[versionBits] || `unknown(${versionBits})`;
  const algorithm = ALGORITHM_MAP[algorithmBits] || `unknown(${algorithmBits})`;

  const byte2 = decoded[1];
  const otpLengthBits = (byte2 >> 5) & 0x07;
  const otpLength = OTP_LENGTH_MAP[otpLengthBits] || `unknown(${otpLengthBits})`;
  const timeStepBit = (byte2 >> 4) & 0x01;
  const timesteps = timeStepBit === 0 ? 30 : 60;
  const typeBits = (byte2 >> 2) & 0x03;
  const tokenType = TYPE_MAP[typeBits] || `unknown(${typeBits})`;
  const protocolBits = byte2 & 0x03;
  const protocol = PROTOCOL_MAP[protocolBits] || `unknown(${protocolBits})`;

  const hostnameBits = Array.from(decoded.slice(2, 29))
    .map((value) => value.toString(2).padStart(8, '0'))
    .join('');
  const chars = [];
  for (let i = 0; i < hostnameBits.length; i += 6) {
    const chunk = hostnameBits.slice(i, i + 6);
    if (chunk === '111111') {
      break;
    }
    chars.push(CHAR_MAP[chunk] || '?');
  }
  const hostname = chars.join('');

  const portBytes = decoded.slice(29, 31);
  let port = (portBytes[0] << 8) + portBytes[1];
  if (port === 0) {
    port = 443;
  }

  const byte32 = decoded[31];
  const allowRootedDevice = Boolean((byte32 >> 7) & 0x01);
  const apiSpecBit = (byte32 >> 6) & 0x01;
  const apiSpec = apiSpecBit === 1 ? 'FTC' : 'FGD';

  const authBytes = Array.from(decoded.slice(32, 40))
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('')
    .toUpperCase();

  return {
    version,
    algorithm,
    otpLength,
    timesteps,
    tokenType,
    protocol,
    hostname,
    port,
    allowRootedDevice,
    apiSpec,
    authBytes,
  };
};

function FortiTokenDecoder() {
  const [form] = Form.useForm();
  const [decoded, setDecoded] = useState(null);
  const [error, setError] = useState(null);

  const handleDecode = (values) => {
    try {
      const result = decodeToken(values.token);
      setDecoded(result);
      setError(null);
    } catch (err) {
      setDecoded(null);
      setError(err.message || 'Failed to decode token.');
    }
  };

  const handleReset = () => {
    form.resetFields();
    setDecoded(null);
    setError(null);
  };

  const descriptionItems = useMemo(() => {
    if (!decoded) {
      return [];
    }

    return [
      { label: 'Version', value: decoded.version },
      { label: 'Algorithm', value: decoded.algorithm },
      { label: 'OTP Length', value: decoded.otpLength },
      { label: 'Time Steps', value: `${decoded.timesteps} seconds` },
      { label: 'Token Type', value: decoded.tokenType },
      { label: 'Protocol', value: decoded.protocol },
      { label: 'Hostname', value: decoded.hostname || 'N/A' },
      { label: 'Port', value: decoded.port },
      { label: 'Allow Rooted Device', value: decoded.allowRootedDevice ? 'Yes' : 'No' },
      { label: 'API Spec', value: decoded.apiSpec },
      { label: 'Auth Bytes', value: decoded.authBytes },
    ];
  }, [decoded]);

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2} style={{ marginBottom: 4 }}>FortiToken Cloud Token Decoder</Title>
        <Paragraph type="secondary">
          Decode FortiToken Cloud activation tokens into their version, hostname, and metadata fields.
          Paste a Base32 token to inspect its parameters.
        </Paragraph>
      </div>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleDecode}
          initialValues={{ token: '' }}
        >
          <Form.Item
            label="Activation Token"
            name="token"
            rules={[{ required: true, message: 'Please enter a FortiToken Cloud token.' }]}
          >
            <Input.TextArea rows={3} placeholder="Enter the Base32-encoded token" />
          </Form.Item>

          <Space>
            <Button type="primary" htmlType="submit">Decode Token</Button>
            <Button onClick={handleReset}>Clear</Button>
          </Space>
        </Form>

        {error && (
          <Alert
            style={{ marginTop: 16 }}
            type="error"
            message="Unable to decode token"
            description={error}
            showIcon
          />
        )}
      </Card>

      <Card>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Title level={4} style={{ margin: 0 }}>Decoded Output</Title>
          <Text type="secondary">Parsed fields derived from the FortiToken Cloud token payload.</Text>
        </Space>
        <Divider style={{ margin: '16px 0' }} />
        {decoded ? (
          <Descriptions column={1} bordered>
            {descriptionItems.map((item) => (
              <Descriptions.Item key={item.label} label={item.label}>
                {item.value}
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : (
          <Text type="secondary">No decoded token yet. Submit a token to view details.</Text>
        )}
      </Card>
    </Space>
  );
}

export default FortiTokenDecoder;
