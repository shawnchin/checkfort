import re

from pygments.lexer import RegexLexer, include
from pygments.token import Text, Comment, Operator, Keyword
from pygments.token import Name, String, Number, Punctuation


class FortranLexer(RegexLexer):
    """Lexer for FORTRAN code"""

    name = 'Fortran'
    aliases = ['fortran']
    filenames = ['*.f', '*.F', '*.f90', '*.F90']
    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'\nC.*', Comment),
            (r'!.*', Comment),
            include('strings'),
            include('core'),
            (r'[a-z][a-z0-9_]*', Name.Variable),
            include('nums'),
            (r'[\s]+', Text),
        ],

        'core': [
            (r'\b('
            # Fortran 77 keywords
            r'access|assign|backspace|blank|block|call|close|common|'
            r'continue|data|dimension|direct|do|else|endif|enddo|'
            r'end|entry|eof|equivalence|err|exist|external|file|'
            r'fmt|form|format|formatted|function|goto|if|implicit|'
            r'include|inquire|intrinsic|iostat|logical|named|'
            r'include|inquire|intrinsic|iostat|logical|named|'
            r'namelist|nextrec|number|open|opened|parameter|pause|'
            r'print|program|read|rec|recl|return|rewind|sequential|'
            r'status|stop|subroutine|then|type|unformatted|unit|write|save|'

            # Fortran 90 keywords
            r'allocate|allocatable|case|contains|cycle|deallocate|default|'
            r'elsewhere|exit|interface|intent|module|only|operator|'
            r'optional|pointer|private|procedure|public|result|recursive|'
            r'select|sequence|target|use|while|where|'

            # Fortran 95 keywords
            r'elemental|forall|pure|'

            # Fortan 2003 keywords
            r'abstract|associate|class|decimal|decorate|delegate|encoding|'
            r'endfile|enum|enumerator|extends|extensible|flush|generic|'
            r'iomsg|import|move_alloc|nextrec|non_overridable|pass|'
            r'pending|reference|round|sign|static|typealias|'

            # Fortran 2003 attributes
            r'asynchronous|bind|protected|volatile|'

            # Non-standard keywords allowed by some compilers
            r'accept|array|byte|decode|encode|extrinsic|nullify|none|options'

            r')\s*\b', Keyword),

            (r'\b('
            r'character|complex|double precision|double complex|'
            r'integer|logical|real'
            r')\s*\b', Keyword.Type),

            # Operators
            (r'(\*\*|\*|\+|-|\/|<|>|<=|>=|==|\/=|=)', Operator),

            (r'(::)', Keyword.Declaration),

            (r'[(),:&%;]', Punctuation),

            (r'\b('
            # Fortran 77 intrinsic functions
            r'abs|achar|acos|aimag|aint|alog|alog10|amax0|amax1|'
            r'amin0|amin1|amod|anint|asin|atan|atan2|cabs|ccos|cexp|'
            r'char|clog|cmplx|conjg|cos|cosh|csin|csqrt|dabs|dacos|'
            r'dasin|datan|datan2|dble|dcos|dcosh|ddim|dexp|dim|dint|'
            r'dlog|dlog10|dmax1|dmin1|dmod|dnint|dprod|dsign|dsinh|dsin|'
            r'dsqrt|dtanh|dtan|dtime|exp|float|iabs|idim|idint|idnint|'
            r'ifix|index|int|isign|len|lge|lgt|lle|llt|log|log10|max|'
            r'min|mod|nint|real|sign|sin|sngl|sqrt|tan|tanh|'

            # Fortran 95 intrinsic functions
            r'adjustl|adjustr|all|allocated|any|associated|bit_size|'
            r'btest|ceiling|count|cpu_time|cshift|date_and_time|digits|'
            r'dot_product|eoshift|epsilon|exponent|floor|fraction|'
            r'huge|iachar|iand|ibclr|ibits|ibset|ichar|ieor|ior|'
            r'ishft|ishftc|kind|lbound|len_trim|logical|matmul|'
            r'maxexponent|maxloc|maxval|merge|minexponent|minloc|'
            r'minval|modulo|mvbits|nearest|not|null|pack|precision|'
            r'present|product|radix|random_number|random_seed|range|'
            r'repeat|reshape|rrspacing|scale|scan|selected_int_kind|'
            r'selected_real_kind|set_exponent|shape|sinh|size|spacing|'
            r'spread|sum|system_clock|tiny|transfer|transpose|trim|'
            r'ubound|unpack|verify|'

            # Fortran 2003 intrinsic functions
            r'c_associated|c_f_pointer|c_f_procpointer|c_funloc|c_loc|'
            r'command_argument_count|get_command|get_command_argument|'
            r'get_environment_variable|is_iostat_end|is_iostat_eor|'
            r'move_alloc|new_line|'

            # GNU extensions
            r'abort|access|acosh|alarm|and|asinh|atanh|besj0|besj1|'
            r'besjn|besjn|besy0|besy1|besyn|besyn|chdir|chmod|ctime|'
            r'dcmplx|dfloat|erf|erfc|etime|exit|fdate|fget|fgetc|flush|'
            r'fnum|fputc|fput|free|fseek|fstat|ftell|gamma|gerror|'
            r'getarg|getcwd|getenv|getgid|getlog|getpid|getuid|'
            r'gmtime|hostnm|iargc|idate|ierrno|imagpart|int2|int8'
            r'irand|isatty|isnan|itime|kill|lgamma|link|lnblnk|loc|'
            r'long|lshift|lstat|ltime|malloc|mclock|mclock8|or|perror|'
            r'ran|rand|realpart|rename|rshift|secnds|second|short|'
            r'signal|sizeof|sleep|srand|stat|symlnk|system|time|time8|'
            r'ttynam|umask|unlink|xor|'

            # f2c extensions
            r'imag|zabs|zcos|zexp|zlog|zsin|zsqrt'
            r')\s*\b', Name.Builtin),

            # Booleans
            (r'\.(true|false)\.', Name.Builtin),
            # Comparing Operators
            (r'\.(eq|ne|lt|le|gt|ge|not|and|or|eqv|neqv)\.', Operator.Word),
        ],

        'strings': [
            (r'(?s)"(\\\\|\\[0-7]+|\\.|[^"\\])*"', String.Double),
            (r"(?s)'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
        ],

        'nums': [
            (r'\d+(?![.Ee])', Number.Integer),
            (r'[+-]?\d*\.\d+([eE][-+]?\d+)?', Number.Float),
            (r'[+-]?\d+\.\d*([eE][-+]?\d+)?', Number.Float),
        ],
    }
