import Cryptodome
from Cryptodome import Random
from Cryptodome.Cipher.PKCS1_OAEP import PKCS1OAEP_Cipher
from Cryptodome.Util.number import ceil_div, bytes_to_long, long_to_bytes
from Cryptodome.Util.py3compat import bord
from Cryptodome.Util.strxor import strxor


class MyOAEP(PKCS1OAEP_Cipher):
    def decrypt(self, ciphertext):
        """Decrypt a message with PKCS#1 OAEP.

        :param ciphertext: The encrypted message.
        :type ciphertext: bytes/bytearray/memoryview

        :returns: The original message (plaintext).
        :rtype: bytes

        :raises ValueError:
            if the ciphertext has the wrong length, or if decryption
            fails the integrity check (in which case, the decryption
            key is probably wrong).
        :raises TypeError:
            if the RSA key has no private half (i.e. you are trying
            to decrypt using a public key).
        """

        # See 7.1.2 in RFC3447
        modBits = Cryptodome.Util.number.size(self._key.n)
        k = ceil_div(modBits, 8)  # Convert from bits to bytes
        hLen = self._hashObj.digest_size

        # Step 1b and 1c
        if len(ciphertext) != k:
            raise ValueError("Ciphertext with incorrect length.")
        # Step 2a (O2SIP)
        ct_int = bytes_to_long(ciphertext)
        # Step 2b (RSADP)
        #m_int = self._key._decrypt(ct_int)
        m_int = pow(ct_int,self._key.e,self._key.n)

        # Complete step 2c (I2OSP)
        em = long_to_bytes(m_int, k)
        # Step 3a
        lHash = self._hashObj.new(self._label).digest()
        # Step 3b
        y = em[0]
        # y must be 0, but we MUST NOT check it here in order not to
        # allow attacks like Manger's (http://dl.acm.org/citation.cfm?id=704143)
        maskedSeed = em[1:hLen + 1]
        maskedDB = em[hLen + 1:]
        # Step 3c
        seedMask = self._mgf(maskedDB, hLen)
        # Step 3d
        seed = strxor(maskedSeed, seedMask)
        # Step 3e
        dbMask = self._mgf(seed, k - hLen - 1)
        # Step 3f
        db = strxor(maskedDB, dbMask)
        # Step 3g
        one_pos = db[hLen:].find(b'\x01')
        lHash1 = db[:hLen]
        invalid = bord(y) | int(one_pos < 0)
        hash_compare = strxor(lHash1, lHash)
        for x in hash_compare:
            invalid |= bord(x)
        for x in db[hLen:one_pos]:
            invalid |= bord(x)
        if invalid != 0:
            raise ValueError("Incorrect decryption.")
        # Step 4
        return db[hLen + one_pos + 1:]

def new(key, hashAlgo=None, mgfunc=None, label=b'', randfunc=None):
    if randfunc is None:
        randfunc = Random.get_random_bytes
    return MyOAEP(key, hashAlgo, mgfunc, label, randfunc)

#for testing
def notrandom(x):
    if x == 32:
        return b'\xf56\xccL`\x8a\x97l\nX0\xf4\x11\x9a\x0e\xce\x99K^\xe6\xcbU\xf3W+It"\xf5\x84\x1d\xe6'
    else:
        return None
